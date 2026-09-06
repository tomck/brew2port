class Brew2port < Formula
  include Language::Python::Virtualenv
  desc "Safe Homebrew to MacPorts migration planner"
  homepage "https://github.com/tomck/brew2port"
  url "https://github.com/tomck/homebrew-brew2port/archive/refs/tags/v0.1.0.tar.gz"
  sha256 "REPLACE_AFTER_RELEASE"
  license "MIT"
  depends_on "python@3.12"

  def install
    virtualenv_install_with_resources
  end

  test do
    system bin/"brew2port", "--help"
  end
end
