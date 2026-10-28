{ pkgs ? import <nixpkgs> {}, ... }:

let
  python = pkgs.python313.withPackages (ps: with ps; [ shapely fonttools numpy pytest ]);
in
pkgs.mkShell {
  packages = with pkgs; [ nodejs_24 python ruff ];
}
