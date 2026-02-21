"""Interface en ligne de commande minimale pour ClaimGuardAI."""

import argparse
import json
import sys

from claimguard.validation import validate_claim


def main():
    parser = argparse.ArgumentParser(
        description="Valide un dossier composé d'ordonnance, facture et feuille de soin"
    )
    parser.add_argument("ordonnance", help="chemin vers l'ordonnance (image/pdf)")
    parser.add_argument("facture", help="chemin vers la facture (image/pdf)")
    parser.add_argument("feuille", help="chemin vers la feuille de soin (image/pdf)")
    args = parser.parse_args()

    try:
        result = validate_claim(args.ordonnance, args.facture, args.feuille)
    except Exception as e:
        print(f"Erreur lors de l'analyse : {e}", file=sys.stderr)
        sys.exit(1)

    # afficher résultat JSON sur stdout
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
