class Brew2port < Formula
  include Language::Python::Virtualenv
  desc "Safe Homebrew to MacPorts migration planner"
  homepage "https://github.com/tomck/brew2port"
  url "https://github.com/tomck/homebrew-brew2port/archive/refs/tags/v0.3.0.tar.gz"
  sha256 "8ee91a4515a710fbc8af2e0b2b90ae0001af0d6394db681f1ae5413c03cf542c"
  license "MIT"
  depends_on "python@3.14"
  depends_on "tomck/escapefrombrewyork/macpkgmap"

def install
  libexec.install "brew2port"

  (bin/"brew2port").write <<~EOS
    #!/bin/sh
    export PYTHONPATH="#{libexec}${PYTHONPATH:+:$PYTHONPATH}"
    exec "#{Formula["python@3.14"].opt_bin}/python3.14" -m brew2port "$@"
  EOS
  chmod 0755, bin/"brew2port"
end

  test do
    system bin/"brew2port", "--help"
  end
end
