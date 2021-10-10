{ pkgs ? import <nixpkgs> { } }:

pkgs.stdenv.mkDerivation {
  name = "j2cli-test";
  version = "unset";
  src = pkgs.lib.cleanSource ./.;
  dontInstall = true;
  buildInputs = [
    pkgs.j2cli
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

    cat strings.yml mdoc.yml > .strings.mdoc.yml
    cat strings.yml plain.yml > .strings.plain.yml

    j2 -o $out/manpage.1 --customize mdoc.j2.py manpage.1.j2 .strings.plain.yml
    j2 -o $out/manpage.1 --customize mdoc.j2.py $out/manpage.1 .strings.plain.yml
    # make a plaintext copy
    groff -m mdoc -T utf8 $out/manpage.1 > $out/manpage.1.txt

    j2 -o $out/markdown.md --customize plain.j2.py markdown.md.j2 .strings.plain.yml
    j2 -o $out/markdown.md --customize plain.j2.py $out/markdown.md .strings.plain.yml

    j2 -o $out/strings.py --customize plain.j2.py strings.py.j2 .strings.plain.yml
    j2 -o $out/strings.py --customize plain.j2.py $out/strings.py .strings.plain.yml
  '';
}


