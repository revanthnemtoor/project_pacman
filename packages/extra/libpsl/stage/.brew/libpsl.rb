class Libpsl < Formula
  desc "C library for the Public Suffix List"
  homepage "https://rockdaboot.github.io/libpsl"
  url "https://github.com/rockdaboot/libpsl/releases/download/0.22.0/libpsl-0.22.0.tar.gz"
  mirror "http://distfiles.macports.org/libpsl/libpsl-0.22.0.tar.gz"
  sha256 "c45c3aa17576b99873e05a9b09a44041b065bbfa390e6d474d06fbfaeb9c7722"
  license "MIT"
  compatibility_version 1

  depends_on "pkgconf" => :build

  on_system :linux, macos: :monterey_or_older do
    depends_on "libidn2"
    depends_on "libunistring"
  end

  def install
    runtime = (OS.linux? || MacOS.version <= :monterey) ? "libidn2" : "libicucore"
    args = %W[
      --disable-silent-rules
      --enable-builtin
      --enable-runtime=#{runtime}
    ]
    system "./configure", *args, *std_configure_args
    system "make", "install"
  end

  test do
    (testpath/"test.c").write <<~C
      #include <assert.h>
      #include <stdio.h>
      #include <string.h>

      #include <libpsl.h>

      int main(void)
      {
          const psl_ctx_t *psl = psl_builtin();

          const char *domain = ".eu";
          assert(psl_is_public_suffix(psl, domain));

          const char *host = "www.example.com";
          const char *expected_domain = "example.com";
          const char *actual_domain = psl_registrable_domain(psl, host);
          assert(strcmp(actual_domain, expected_domain) == 0);

          return 0;
      }
    C
    system ENV.cc, "-o", "test", "test.c", "-I#{include}", "-L#{lib}", "-lpsl"
    system "./test"
  end
end
