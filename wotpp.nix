{ pkgs ? import <nixpkgs> { } }:

let
  wotpp = pkgs.stdenv.mkDerivation {
    name = "wotpp";
    version = "unset";
    src = pkgs.fetchFromGitHub {
      owner = "wotpp";
      repo = "wotpp";
      rev = "d67fcc86388b9505303d7106b7118e9d67bca1b5";
      hash = "sha256-yqX70imRQNwpEHuZiqsAiyM7gHLm6hH9dxVeCQF17xU=";
    };
    nativeBuildInputs = [ pkgs.meson pkgs.ninja ];
    buildInputs = [];
  };

in
pkgs.stdenv.mkDerivation {
  name = "wotpp-test";
  version = "unset";
  src = pkgs.lib.cleanSource ./.;
  dontInstall = true;
  buildInputs = [
    wotpp
    pkgs.groff
  ];
  buildPhase = ''
    mkdir $out

    w++ manpage.wpp > $out/manpage.1
    # make a plaintext copy
    groff -m mdoc -T utf8 $out/manpage.1 > $out/manpage.1.txt

    w++ markdown.wpp > $out/markdown.md

    w++ strings.wpp > $out/strings.py
  '';
}
