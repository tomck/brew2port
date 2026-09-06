class Brew2port < Formula
  include Language::Python::Virtualenv
  desc "Safe Homebrew to MacPorts migration planner"
  homepage "https://github.com/tomck/brew2port"
  url "https://github.com/tomck/homebrew-brew2port/archive/refs/tags/v0.1.0.tar.gz"
  sha256 "686e700d86fc4bf78fc98976773365498902ef1cd6ee83da7ae47d110a7c67ce"
  license "MIT"
  depends_on "python@3.14"

  def install
    virtualenv_install_with_resources
  end

  test do
    system bin/"brew2port", "--help"
  end
end
