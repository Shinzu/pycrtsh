"""CLI for pycrtsh api functions."""
import argparse
import datetime
import json

from prettytable import PrettyTable

from .api import Crtsh


def datetime_handler(dtime):
    """Convert datetime object."""
    if isinstance(dtime, datetime.datetime):
        return dtime.isoformat()
    raise TypeError("Unknown type")


def main():
    """Provide CLI Arguments and prints data."""
    parser = argparse.ArgumentParser(description="Request crt.sh")
    subparsers = parser.add_subparsers(help="Commands")
    parser_a = subparsers.add_parser(
        "cert", help="Query a certificate (id, sha1, sha256 or serial)"
    )
    parser_a.add_argument(
        "VALUE",
        help="Value to be requested, can be a crt.sh id, sha1, sha256 or serial",
    )
    parser_a.set_defaults(which="cert")
    parser_b = subparsers.add_parser("domain", help="List certs related to a domain")
    parser_b.add_argument("DOMAIN", help="domain")
    parser_b.set_defaults(which="domain")
    parser_b.add_argument(
        "--caid",
        action="store",
        dest="caid",
        help="Define with which CA ID the search should be narrowed",
        default=None,
    )
    parser_b.add_argument(
        "--exclude",
        action="store",
        dest="exclude",
        help='Define wich certificates should be excluded, \
                for now only the keyword "expired" is supported',
        default=None,
    )
    args = parser.parse_args()

    if hasattr(args, "which"):
        crt = Crtsh()
        if args.which == "cert":
            types = {32: "serial", 40: "sha1", 64: "sha256"}
            try:
                ctype = types[len(args.VALUE)]
            except KeyError:
                ctype = "id"
            res = crt.get(args.VALUE, ctype=ctype)
            print(json.dumps(res, sort_keys=True, indent=4, default=datetime_handler))
        elif args.which == "domain":
            res = crt.search(args.DOMAIN, args.caid, args.exclude)
            if len(res) == 0:
                print("No certificate found!")

            table = PrettyTable()
            table.field_names = [
                "ID",
                "Logged at",
                "Not Before",
                "Not After",
                "SAN",
                "CA",
            ]

            for obj in res:
                row = [
                    obj["id"],
                    obj["logged_at"].isoformat(),
                    obj["not_before"].isoformat(),
                    obj["not_after"].isoformat(),
                    obj["name"],
                    obj["ca"]["name"],
                ]
                table.add_row(row)

            print(table)

        else:
            parser.print_help()

    else:
        parser.print_help()
