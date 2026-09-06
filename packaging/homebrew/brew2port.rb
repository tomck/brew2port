class Brew2port < Formula
  desc "Safe Homebrew to MacPorts migration planner"
  homepage "https://github.com/example/brew2port"
  url "https://github.com/example/brew2port/archive/refs/tags/v0.1.0.tar.gz"
  sha256 "REPLACE_WITH_RELEASE_SHA256"
  license "MIT"
  depends_on "python@3.12"
  def install
    system "python3", "-m", "pip", "install", *std_pip_args, "."
  end
  test do
    system bin/"brew2port", "--help"
  end
end
