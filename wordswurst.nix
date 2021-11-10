{ pkgs ? import <nixpkgs> { } }:

pkgs.stdenv.mkDerivation {
  name = "wordswurst-test";
  version = "unset";
  src = pkgs.lib.cleanSource ./.;
  dontInstall = true;
  buildInputs = [
    pkgs.python39
    pkgs.python39.pkgs.tinycss2
    pkgs.python39.pkgs.cssselect2
    pkgs.groff
  ];
  /*
  This repeats each j2 stage twice because it's
  double-templating--a normal jinja template, and
  jinja template tags in the yaml. The first round
  will substitute them down into the jinja template
  and the second round will substitute any "new"
  tags that snuck in with the yaml.
  */
  buildPhase = ''
    mkdir $out

    python3 wordswurst.py manpage.wwst > $out/manpage.1
    # make a plaintext copy
    groff -m mdoc -T utf8 $out/manpage.1 > $out/manpage.1.txt

    python3 wordswurst.py markdown.wwst > $out/markdown.md

    python3 wordswurst.py strings.wwst > $out/strings.py
  '';
}


