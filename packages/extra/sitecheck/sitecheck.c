/*
 * sitecheck.c - Minimal native macOS CLI utility for website availability,
 *               DNS resolution, HTTP status codes, and connection diagnostics.
 *
 * Uses only base macOS libc / POSIX APIs plus system /usr/bin/curl and /usr/bin/dig.
 */

#include <ctype.h>
#include <errno.h>
#include <fcntl.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

typedef struct {
    int code;
    const char *status;
    const char *reason;
} StatusEntry;

static const StatusEntry CURL_ERROR_TABLE[] = {
    {3,  "CONNECTION FAILED", "URL malformed or invalid syntax (curl exit 3)"},
    {5,  "CONNECTION FAILED", "Could not resolve proxy (curl exit 5)"},
    {6,  "CONNECTION FAILED", "DNS resolution failed — could not resolve host (curl exit 6)"},
    {7,  "CONNECTION FAILED", "Failed to connect to host — connection refused or unreachable (curl exit 7)"},
    {28, "CONNECTION FAILED", "Connection or operation timed out (curl exit 28)"},
    {35, "CONNECTION FAILED", "SSL/TLS handshake failed (curl exit 35)"},
    {47, "CONNECTION FAILED", "Too many redirects (curl exit 47)"},
    {51, "CONNECTION FAILED", "SSL/TLS peer certificate verification failed (curl exit 51)"},
    {52, "CONNECTION FAILED", "Server returned an empty reply without headers (curl exit 52)"},
    {56, "CONNECTION FAILED", "Network failure while receiving data from peer (curl exit 56)"},
    {60, "CONNECTION FAILED", "SSL/TLS peer certificate verification failed (curl exit 60)"},
};

static const StatusEntry HTTP_ERROR_TABLE[] = {
    {400, "BAD REQUEST",           "Server could not understand the request due to invalid syntax (HTTP 400)"},
    {401, "UNAUTHORIZED",          "Authentication is required to access this resource (HTTP 401)"},
    {403, "FORBIDDEN",             "Server understood the request but refuses to authorize it — access denied or WAF blocked (HTTP 403)"},
    {404, "NOT FOUND",             "The requested resource or page could not be found on the server (HTTP 404)"},
    {429, "TOO MANY REQUESTS",     "Rate limit exceeded — client has sent too many requests in a given window (HTTP 429)"},
    {500, "INTERNAL SERVER ERROR", "Origin server encountered an unexpected condition (HTTP 500)"},
    {502, "BAD GATEWAY",           "Reverse proxy or gateway received an invalid response from the upstream server (HTTP 502)"},
    {503, "SERVICE UNAVAILABLE",   "Server is temporarily overloaded or under maintenance and cannot handle the request (HTTP 503)"},
    {504, "GATEWAY TIMEOUT",       "Upstream server failed to respond in time to the gateway or proxy (HTTP 504)"},
};

static void print_help(void) {
    printf(
        "Usage: sitecheck [-dns <DNS_IP>] <URL>\n"
        "\n"
        "Diagnose website availability, HTTP status codes, DNS resolution,\n"
        "connection failures, and response times.\n"
        "\n"
        "Options:\n"
        "  -dns, --dns <IP>   Use custom DNS resolver (e.g. 1.1.1.1, 8.8.8.8, 9.9.9.9)\n"
        "  -h, --help         Display this help message\n"
        "\n"
        "Examples:\n"
        "  sitecheck https://github.com\n"
        "  sitecheck https://citizenx.com\n"
        "  sitecheck -dns 1.1.1.1 https://citizenx.com\n"
        "  sitecheck -dns 8.8.8.8 https://citizenx.com\n"
        "  sitecheck -dns 9.9.9.9 https://citizenx.com\n"
    );
}

static bool is_valid_ipv4(const char *s) {
    if (!s || !*s) {
        return false;
    }

    int dots = 0;
    const char *p = s;

    while (*p) {
        if (!isdigit((unsigned char)*p)) {
            return false;
        }
        int digits = 0;
        int val = 0;
        while (*p && isdigit((unsigned char)*p)) {
            val = val * 10 + (*p - '0');
            digits++;
            if (digits > 3 || val > 255) {
                return false;
            }
            p++;
        }
        if (*p == '.') {
            dots++;
            if (dots > 3) {
                return false;
            }
            p++;
            if (!*p) {
                return false;
            }
        } else if (*p != '\0') {
            return false;
        }
    }

    return dots == 3;
}

static bool is_valid_hostname(const char *host) {
    if (!host || !*host) {
        return false;
    }
    size_t total_len = strlen(host);
    if (total_len > 253) {
        return false;
    }

    size_t label_len = 0;
    bool prev_alnum = false;

    for (size_t i = 0; i < total_len; i++) {
        unsigned char c = (unsigned char)host[i];
        if (c == '.') {
            if (label_len == 0 || !prev_alnum) {
                return false;
            }
            label_len = 0;
            prev_alnum = false;
        } else if (isalnum(c)) {
            if (label_len >= 63) {
                return false;
            }
            label_len++;
            prev_alnum = true;
        } else if (c == '-') {
            if (label_len == 0 || label_len >= 63) {
                return false;
            }
            label_len++;
            prev_alnum = false;
        } else {
            return false;
        }
    }

    return label_len > 0 && prev_alnum;
}

static bool str_eq_ci(const char *a, const char *b) {
    while (*a && *b) {
        if (tolower((unsigned char)*a) != tolower((unsigned char)*b)) {
            return false;
        }
        a++;
        b++;
    }
    return *a == '\0' && *b == '\0';
}

static bool parse_url(const char *raw_url, char *norm_out, size_t norm_sz,
                      char *host_out, size_t host_sz, int *port_out,
                      bool *default_scheme_out, bool *explicit_port_out) {
    int default_port = 443;
    const char *rest = NULL;
    bool default_scheme = false;

    if (strncmp(raw_url, "https://", 8) == 0) {
        default_port = 443;
        rest = raw_url + 8;
        snprintf(norm_out, norm_sz, "%s", raw_url);
    } else if (strncmp(raw_url, "http://", 7) == 0) {
        default_port = 80;
        rest = raw_url + 7;
        snprintf(norm_out, norm_sz, "%s", raw_url);
    } else if (strstr(raw_url, "://") != NULL) {
        fprintf(stderr, "Error: Invalid or malformed URL: '%s' (expected http:// or https:// URL)\n", raw_url);
        return false;
    } else {
        default_scheme = true;
        default_port = 443;
        rest = raw_url;
        if (snprintf(norm_out, norm_sz, "https://%s", raw_url) >= (int)norm_sz) {
            fprintf(stderr, "Error: URL too long: '%s'\n", raw_url);
            return false;
        }
    }

    if (!*rest) {
        fprintf(stderr, "Error: Invalid or malformed URL: '%s' (expected http:// or https:// URL)\n", raw_url);
        return false;
    }

    /* Authority ends at '/', '?', '#', or NUL */
    const char *auth_end = rest;
    while (*auth_end && *auth_end != '/' && *auth_end != '?' && *auth_end != '#') {
        if (*auth_end == '@') {
            fprintf(stderr, "Error: Invalid or malformed URL: '%s' (userinfo '@' not supported)\n", raw_url);
            return false;
        }
        auth_end++;
    }

    size_t auth_len = (size_t)(auth_end - rest);
    if (auth_len == 0) {
        fprintf(stderr, "Error: Invalid or malformed URL: '%s' (missing host)\n", raw_url);
        return false;
    }

    const char *colon = memchr(rest, ':', auth_len);
    size_t host_len = colon ? (size_t)(colon - rest) : auth_len;

    if (host_len == 0 || host_len >= host_sz) {
        fprintf(stderr, "Error: Invalid or malformed URL: '%s' (invalid host length)\n", raw_url);
        return false;
    }

    memcpy(host_out, rest, host_len);
    host_out[host_len] = '\0';

    if (default_scheme && !strchr(host_out, '.') && !str_eq_ci(host_out, "localhost")) {
        fprintf(stderr, "Error: Invalid or malformed URL: '%s' (expected http:// or https:// URL)\n", raw_url);
        return false;
    }

    if (!is_valid_hostname(host_out)) {
        fprintf(stderr, "Error: Invalid hostname '%s' in URL '%s'\n", host_out, raw_url);
        return false;
    }

    int port = default_port;
    bool explicit_port = false;
    if (colon) {
        const char *port_str = colon + 1;
        size_t port_len = (size_t)(auth_end - port_str);
        if (port_len == 0 || port_len > 5) {
            fprintf(stderr, "Error: Invalid or malformed port in URL '%s'\n", raw_url);
            return false;
        }
        long parsed_port = 0;
        for (size_t i = 0; i < port_len; i++) {
            if (!isdigit((unsigned char)port_str[i])) {
                fprintf(stderr, "Error: Invalid or malformed port in URL '%s'\n", raw_url);
                return false;
            }
            parsed_port = parsed_port * 10 + (port_str[i] - '0');
        }
        if (parsed_port < 1 || parsed_port > 65535) {
            fprintf(stderr, "Error: Invalid port '%ld' in URL '%s'\n", parsed_port, raw_url);
            return false;
        }
        port = (int)parsed_port;
        explicit_port = true;
    }

    *port_out = port;
    *default_scheme_out = default_scheme;
    *explicit_port_out = explicit_port;
    return true;
}

static int run_command_capture(const char *const argv[], char *out_buf, size_t out_sz) {
    int pipefd[2];
    if (pipe(pipefd) != 0) {
        return -1;
    }

    pid_t pid = fork();
    if (pid < 0) {
        close(pipefd[0]);
        close(pipefd[1]);
        return -1;
    }

    if (pid == 0) {
        close(pipefd[0]);
        dup2(pipefd[1], STDOUT_FILENO);
        close(pipefd[1]);

        int devnull = open("/dev/null", O_WRONLY);
        if (devnull >= 0) {
            dup2(devnull, STDERR_FILENO);
            close(devnull);
        }

        execvp(argv[0], (char *const *)argv);
        _exit(127);
    }

    close(pipefd[1]);

    size_t total = 0;
    while (total + 1 < out_sz) {
        ssize_t n = read(pipefd[0], out_buf + total, out_sz - 1 - total);
        if (n < 0) {
            if (errno == EINTR) {
                continue;
            }
            break;
        }
        if (n == 0) {
            break;
        }
        total += (size_t)n;
    }
    out_buf[total] = '\0';
    close(pipefd[0]);

    int status = 0;
    while (waitpid(pid, &status, 0) < 0) {
        if (errno != EINTR) {
            return -1;
        }
    }

    if (WIFEXITED(status)) {
        return WEXITSTATUS(status);
    }
    return 1;
}

static const char *dns_provider_label(const char *dns_ip) {
    if (strcmp(dns_ip, "1.1.1.1") == 0 || strcmp(dns_ip, "1.0.0.1") == 0) {
        return "Cloudflare DNS";
    }
    if (strcmp(dns_ip, "8.8.8.8") == 0 || strcmp(dns_ip, "8.8.4.4") == 0) {
        return "Google DNS";
    }
    if (strcmp(dns_ip, "9.9.9.9") == 0 || strcmp(dns_ip, "149.112.112.112") == 0) {
        return "Quad9 DNS";
    }
    return NULL;
}

static bool resolve_with_dig(const char *dns_server, const char *host, char *ip_out, size_t ip_sz) {
    const char *dig_bin = (access("/usr/bin/dig", X_OK) == 0) ? "/usr/bin/dig" : "dig";
    char at_server[64];
    snprintf(at_server, sizeof(at_server), "@%s", dns_server);

    const char *argv[] = {
        dig_bin, at_server, "+time=3", "+tries=2", "+short", "A", host, NULL
    };
    char out[2048];
    int rc = run_command_capture(argv, out, sizeof(out));
    if (rc != 0) {
        return false;
    }

    char *saveptr = NULL;
    for (char *line = strtok_r(out, "\r\n", &saveptr); line; line = strtok_r(NULL, "\r\n", &saveptr)) {
        if (is_valid_ipv4(line)) {
            snprintf(ip_out, ip_sz, "%s", line);
            return true;
        }
    }
    return false;
}

static void report_curl_failure(int curl_rc, const char *host, int port,
                                const char *resolved_ip, const char *remote_ip) {
    if (remote_ip && *remote_ip) {
        printf("Remote IP: %s\n", remote_ip);
    } else if (resolved_ip && *resolved_ip) {
        printf("Remote IP: %s (not connected)\n", resolved_ip);
    } else {
        printf("Remote IP: N/A\n");
    }
    printf("HTTP Status: N/A (Connection Failed)\n");
    printf("Response Time: N/A\n");
    printf("Status: CONNECTION FAILED\n");

    if (curl_rc == 6) {
        printf("Reason: DNS resolution failed — could not resolve host '%s' (curl exit 6)\n", host);
        return;
    }
    if (curl_rc == 7) {
        printf("Reason: Failed to connect to host '%s' on port %d — connection refused or unreachable (curl exit 7)\n", host, port);
        return;
    }

    size_t count = sizeof(CURL_ERROR_TABLE) / sizeof(CURL_ERROR_TABLE[0]);
    for (size_t i = 0; i < count; i++) {
        if (CURL_ERROR_TABLE[i].code == curl_rc) {
            printf("Reason: %s\n", CURL_ERROR_TABLE[i].reason);
            return;
        }
    }
    printf("Reason: curl failed with error code %d\n", curl_rc);
}

static int report_http_status(int http_code) {
    size_t count = sizeof(HTTP_ERROR_TABLE) / sizeof(HTTP_ERROR_TABLE[0]);
    for (size_t i = 0; i < count; i++) {
        if (HTTP_ERROR_TABLE[i].code == http_code) {
            printf("Status: %s\n", HTTP_ERROR_TABLE[i].status);
            printf("Reason: %s\n", HTTP_ERROR_TABLE[i].reason);
            return 1;
        }
    }

    if (http_code >= 200 && http_code <= 299) {
        printf("Status: ONLINE\n");
        printf("Reason: Request succeeded (HTTP %d)\n", http_code);
        return 0;
    }
    if (http_code >= 300 && http_code <= 399) {
        printf("Status: ONLINE (REDIRECT)\n");
        printf("Reason: Redirect response received (HTTP %d)\n", http_code);
        return 0;
    }
    if (http_code >= 400 && http_code <= 499) {
        printf("Status: CLIENT ERROR\n");
        printf("Reason: Server returned client error response (HTTP %d)\n", http_code);
        return 1;
    }
    if (http_code >= 500 && http_code <= 599) {
        printf("Status: SERVER ERROR\n");
        printf("Reason: Server returned server error response (HTTP %d)\n", http_code);
        return 1;
    }

    printf("Status: HTTP ERROR\n");
    printf("Reason: Unexpected HTTP response code (%d)\n", http_code);
    return 1;
}

static int run_curl_probe(const char *url, const char *resolve_spec,
                          char *http_str, size_t http_sz,
                          char *time_str, size_t time_sz,
                          char *remote_ip, size_t remote_sz) {
    const char *curl_bin = (access("/usr/bin/curl", X_OK) == 0) ? "/usr/bin/curl" : "curl";
    const char *curl_argv[16];
    int idx = 0;

    curl_argv[idx++] = curl_bin;
    curl_argv[idx++] = "-L";
    curl_argv[idx++] = "-s";
    curl_argv[idx++] = "-o";
    curl_argv[idx++] = "/dev/null";
    curl_argv[idx++] = "--connect-timeout";
    curl_argv[idx++] = "5";
    curl_argv[idx++] = "--max-time";
    curl_argv[idx++] = "15";
    if (resolve_spec && resolve_spec[0] != '\0') {
        curl_argv[idx++] = "--resolve";
        curl_argv[idx++] = resolve_spec;
    }
    curl_argv[idx++] = "-w";
    curl_argv[idx++] = "%{http_code} %{time_total} %{remote_ip}";
    curl_argv[idx++] = url;
    curl_argv[idx] = NULL;

    char curl_out[512];
    int curl_rc = run_command_capture(curl_argv, curl_out, sizeof(curl_out));

    snprintf(http_str, http_sz, "000");
    if (time_sz > 0) {
        time_str[0] = '\0';
    }
    if (remote_sz > 0) {
        remote_ip[0] = '\0';
    }

    char *sp = NULL;
    char *tok_http = strtok_r(curl_out, " \t\r\n", &sp);
    char *tok_time = strtok_r(NULL, " \t\r\n", &sp);
    char *tok_ip = strtok_r(NULL, " \t\r\n", &sp);
    if (tok_http && *tok_http) {
        snprintf(http_str, http_sz, "%s", tok_http);
    }
    if (tok_time && *tok_time) {
        snprintf(time_str, time_sz, "%s", tok_time);
    }
    if (tok_ip && *tok_ip) {
        snprintf(remote_ip, remote_sz, "%s", tok_ip);
    }
    return curl_rc;
}

static bool should_retry_http(int curl_rc) {
    return curl_rc == 7 || curl_rc == 35 || curl_rc == 51 || curl_rc == 60;
}

static int check_single_url(const char *dns_server, const char *raw_url) {
    char norm_url[2048];
    char host[256];
    int port = 443;
    bool default_scheme = false;
    bool explicit_port = false;

    if (!parse_url(raw_url, norm_url, sizeof(norm_url), host, sizeof(host),
                   &port, &default_scheme, &explicit_port)) {
        return 1;
    }

    printf("Checking %s ...\n", norm_url);

    char resolved_ip[64] = "";
    char resolve_spec[340] = "";

    if (dns_server) {
        const char *label = dns_provider_label(dns_server);
        if (label) {
            printf("DNS Server: %s (%s)\n", dns_server, label);
        } else {
            printf("DNS Server: %s\n", dns_server);
        }

        if (is_valid_ipv4(host)) {
            snprintf(resolved_ip, sizeof(resolved_ip), "%s", host);
        } else if (!resolve_with_dig(dns_server, host, resolved_ip, sizeof(resolved_ip))) {
            printf("Resolved IP: N/A\n");
            printf("HTTP Status: N/A (DNS Resolution Failed)\n");
            printf("Response Time: N/A\n");
            printf("Status: DNS FAILED\n");
            printf("Reason: DNS resolution failed for '%s' using resolver %s\n", host, dns_server);
            return 1;
        }

        printf("Resolved IP: %s\n", resolved_ip);
        snprintf(resolve_spec, sizeof(resolve_spec), "%s:%d:%s", host, port, resolved_ip);
    } else {
        printf("DNS Server: System Default\n");
    }

    char http_str[32];
    char time_str[64];
    char remote_ip[128];
    int curl_rc = run_curl_probe(norm_url, resolve_spec,
                                 http_str, sizeof(http_str),
                                 time_str, sizeof(time_str),
                                 remote_ip, sizeof(remote_ip));

    if (curl_rc != 0 && default_scheme && !explicit_port && should_retry_http(curl_rc)) {
        port = 80;
        snprintf(norm_url, sizeof(norm_url), "http://%s", raw_url);
        if (resolved_ip[0] != '\0') {
            snprintf(resolve_spec, sizeof(resolve_spec), "%s:%d:%s", host, port, resolved_ip);
        }
        printf("HTTPS check failed (curl exit %d); retrying %s ...\n", curl_rc, norm_url);
        curl_rc = run_curl_probe(norm_url, resolve_spec,
                                 http_str, sizeof(http_str),
                                 time_str, sizeof(time_str),
                                 remote_ip, sizeof(remote_ip));
    }

    if (curl_rc != 0) {
        report_curl_failure(curl_rc, host, port, resolved_ip, remote_ip);
        return 1;
    }

    if (remote_ip[0] != '\0') {
        printf("Remote IP: %s\n", remote_ip);
    } else if (resolved_ip[0] != '\0') {
        printf("Remote IP: %s\n", resolved_ip);
    }
    printf("HTTP Status: %s\n", http_str);
    printf("Response Time: %s seconds\n", time_str);

    return report_http_status(atoi(http_str));
}

int main(int argc, char **argv) {
    const char *dns_server = NULL;
    const char **urls = calloc((size_t)argc, sizeof(const char *));
    int url_count = 0;

    if (!urls) {
        fprintf(stderr, "Error: Memory allocation failure\n");
        return 1;
    }

    for (int i = 1; i < argc; i++) {
        const char *arg = argv[i];
        if (strcmp(arg, "-h") == 0 || strcmp(arg, "--help") == 0) {
            print_help();
            free(urls);
            return 0;
        } else if (strcmp(arg, "-dns") == 0 || strcmp(arg, "--dns") == 0) {
            if (i + 1 >= argc) {
                fprintf(stderr, "Error: Missing DNS server IP after %s\n", arg);
                fprintf(stderr, "Usage: sitecheck -dns <DNS_IP> <URL>\n");
                free(urls);
                return 1;
            }
            dns_server = argv[++i];
        } else if (arg[0] == '-') {
            fprintf(stderr, "Error: Unknown option '%s'\n", arg);
            fprintf(stderr, "Usage: sitecheck [-dns <DNS_IP>] <URL>\n");
            free(urls);
            return 1;
        } else {
            urls[url_count++] = arg;
        }
    }

    if (url_count == 0) {
        if (dns_server) {
            fprintf(stderr, "Usage: sitecheck -dns <DNS_IP> <URL>\n");
        } else {
            fprintf(stderr, "Usage: sitecheck [-dns <DNS_IP>] <URL>\n");
        }
        free(urls);
        return 1;
    }

    if (dns_server && !is_valid_ipv4(dns_server)) {
        fprintf(stderr, "Error: Invalid DNS server IP address: '%s'\n", dns_server);
        free(urls);
        return 1;
    }

    int overall_rc = 0;
    for (int i = 0; i < url_count; i++) {
        if (i > 0) {
            printf("\n");
        }
        if (check_single_url(dns_server, urls[i]) != 0) {
            overall_rc = 1;
        }
    }

    free(urls);
    return overall_rc;
}

