class Brew2port < Formula
  include Language::Python::Virtualenv
  desc "Safe Homebrew to MacPorts migration planner"
  homepage "https://github.com/tomck/brew2port"
  url "https://github.com/tomck/homebrew-brew2port/archive/refs/tags/v0.1.5.tar.gz"
  sha256 "bc97fd9e66fb3d460c281b44a6db740133148ebc07361a71f1d2c4f7d758631d"
  license "MIT"
  depends_on "python@3.14"

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
