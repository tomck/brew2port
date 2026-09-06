class Brew2port < Formula
  include Language::Python::Virtualenv
  desc "Safe Homebrew to MacPorts migration planner"
  homepage "https://github.com/tomck/brew2port"
  url "https://github.com/tomck/homebrew-brew2port/archive/refs/tags/v0.1.4.tar.gz"
  sha256 "9a7bd476dba5d0b1f20811c47773fa0ec447d7f50d89ec1694562799299a6059"
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
