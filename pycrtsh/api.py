"""Lib to query crt.sh."""
import re

import requests
from bs4 import BeautifulSoup
from dateutil.parser import parse


class CrtshInvalidRequestType(Exception):

    """Exception if the request is invalid."""

    def __init__(self):
        Exception.__init__(self, "Invalid request type")


class CrtshCertificateNotFound(Exception):

    """Exception if a certificate is not found."""

    def __init__(self):
        Exception.__init__(self, "Certificate not found")


class Crtsh:

    """Main Crtsh object."""

    def __init__(self):
        pass

    @staticmethod
    def search(query, icaid=None, exclude=None):
        """
        Search crt.sh with the give query Query.

        can be domain, sha1, sha256.
        """
        if exclude is not None:
            res = requests.get(
                "https://crt.sh/",
                params={"q": query, "output": "json", "exclude": exclude},
            )
        if exclude is None:
            res = requests.get(
                "https://crt.sh/", params={"q": query, "output": "json"},
            )
        nameparser = re.compile('([a-zA-Z]+)=("[^"]+"|[^,]+)')
        certs = []
        for cert in res.json():
            if icaid is not None and cert["issuer_ca_id"] == int(icaid):
                certs.append(
                    {
                        "id": cert["id"],
                        "logged_at": parse(cert["entry_timestamp"]),
                        "not_before": parse(cert["not_before"]),
                        "not_after": parse(cert["not_after"]),
                        "name": cert["name_value"],
                        "ca": {
                            "caid": cert["issuer_ca_id"],
                            "name": cert["issuer_name"],
                            "parsed_name": dict(
                                nameparser.findall(cert["issuer_name"])
                            ),
                        },
                    }
                )
            if icaid is None:
                certs.append(
                    {
                        "id": cert["id"],
                        "logged_at": parse(cert["entry_timestamp"]),
                        "not_before": parse(cert["not_before"]),
                        "not_after": parse(cert["not_after"]),
                        "name": cert["name_value"],
                        "ca": {
                            "caid": cert["issuer_ca_id"],
                            "name": cert["issuer_name"],
                            "parsed_name": dict(
                                nameparser.findall(cert["issuer_name"])
                            ),
                        },
                    }
                )

        return certs

    @staticmethod
    def get(query, ctype="sha1"):
        """
        Search for a certificate with the given value certificate type.

        can be either a crtsh id, sha1 or sha256.
        """
        # pylint: disable=too-many-branches,too-many-statements
        if ctype not in ["sha1", "sha256", "id"]:
            raise CrtshInvalidRequestType()
        if ctype == "id":
            res = requests.get("https://crt.sh/", params={"id": query})
        else:
            res = requests.get("https://crt.sh/", params={"q": query})

        if "<BR><BR>Certificate not found </BODY>" in res.text:
            raise CrtshCertificateNotFound()
        if "<BR><BR>Invalid value:" in res.text:
            raise CrtshCertificateNotFound()

        soup = BeautifulSoup(res.text, "lxml")
        table = soup.find_all("table")[1]
        cert = {}
        lines1 = table.find_all("tr", recursive=False)
        if len(lines1) < 7:
            # It means that we are in a research
            # not in a certificate description
            # ie https://crt.sh/?q=sha1
            raise CrtshCertificateNotFound()

        cert["id"] = lines1[0].td.text
        cert["summary"] = lines1[1].td.text
        cert["sha256"] = lines1[4].a.text
        cert["sha1"] = lines1[5].td.text
        certinfo = str(lines1[6].td)[60:-6].split("<br/>")
        i = 0
        while i < len(certinfo):
            if "Version:" in certinfo[i]:
                cert["version"] = certinfo[i].strip().split("\xa0")[1]
            if "Serial\xa0Number:" in certinfo[i]:
                # Size of serial may change
                ends = certinfo[i][25:].find('"')
                cert["serial"] = certinfo[i][25 : 25 + ends]  # noqa: E203
            if "Signature\xa0Algorithm:" in certinfo[i]:
                if "signature_algorithm" in cert.keys():
                    signature = ""
                    i += 1
                    while certinfo[i].startswith(
                        "\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0"
                    ):
                        signature += certinfo[i][9:]
                        i += 1
                    i -= 1
                    cert["signature"] = signature.replace(":", "")
                else:
                    cert["signature_algorithm"] = certinfo[i].split(":")[1].strip()
            if ">Issuer:</a>" in certinfo[i]:
                cert["issuer"] = {"id": certinfo[i].split('"')[1][6:]}
                i += 1
                while certinfo[i].startswith(
                    "\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0"
                ):
                    split = certinfo[i].split("=")
                    cert["issuer"][split[0].strip()] = (
                        split[1].strip().replace("\xa0", " ")
                    )
                    i += 1
                i -= 1
            if "\xa0Not\xa0Before:" in certinfo[i]:
                cert["not_before"] = parse(certinfo[i][24:])
            if "\xa0Not\xa0After\xa0:" in certinfo[i]:
                cert["not_after"] = parse(certinfo[i][24:])
            if "\xa0Subject:" in certinfo[i]:
                cert["subject"] = {}
                i += 1
                while certinfo[i].startswith(
                    "\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0"
                ):
                    split = certinfo[i].split("=")
                    cert["subject"][split[0].strip()] = (
                        split[1].strip().replace("\xa0", " ")
                    )
                    i += 1
                i -= 1
            if "Subject\xa0Public\xa0Key\xa0Info:</a>" in certinfo[i]:
                cert["publickey"] = {"sha256": certinfo[i].split("=")[2][:64]}
            if "Public\xa0Key\xa0Algorithm" in certinfo[i]:
                cert["publickey"]["algorithm"] = certinfo[i].split(":")[1].strip()
            if "\xa0Public-Key:\xa0(" in certinfo[i]:
                cert["publickey"]["size"] = int(
                    certinfo[i].split("(")[1].split("\xa0")[0]
                )
            if "\xa0Modulus:" in certinfo[i]:
                modulus = ""
                i += 1
                while certinfo[i].startswith(
                    "\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0"  # noqa: E501 pylint: disable=line-too-long
                ):
                    modulus += certinfo[i][20:]
                    i += 1
                cert["publickey"]["modulus"] = modulus.replace(":", "")
                i -= 1
            if "Exponent:" in certinfo[i]:
                cert["publickey"]["exponent"] = certinfo[i][26:].split("\xa0")[0]
            if "X509v3\xa0extensions:" in certinfo[i]:
                cert["extensions"] = {}
            if "\xa0Subject\xa0Alternative\xa0Name:" in certinfo[i]:
                cert["extensions"]["alternative_names"] = []
                i += 1
                while certinfo[i].startswith(
                    "\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0DNS:"  # noqa: E501 pylint: disable=line-too-long
                ):
                    cert["extensions"]["alternative_names"].append(
                        certinfo[i][20:].strip()
                    )
                    i += 1
                i -= 1
            if "X509v3\xa0Basic\xa0Constraints:\xa0" in certinfo[i]:
                i += 1
                cert["extensions"]["basic_constraints"] = "CA:FALSE" not in certinfo[i]
            if "X509v3\xa0Key\xa0Usage:" in certinfo[i]:
                cert["extensions"]["key_usage"] = {
                    "critical": ("Usage:\xa0critical" in certinfo[i])
                }
                i += 1
                cert["extensions"]["key_usage"]["usage"] = [
                    a.strip().replace("\xa0", " ") for a in certinfo[i].split(",")
                ]
            if "X509v3\xa0CRL\xa0Distribution\xa0Points:" in certinfo[i]:
                i += 3
                cert["extensions"]["crl_distribution"] = {
                    "url": certinfo[i].split("URI:")[1].strip()
                }
            if "X509v3\xa0Extended\xa0Key\xa0Usage:" in certinfo[i]:
                i += 1
                cert["extensions"]["extended_key_usage"] = {
                    "usage": [
                        a.strip().replace("\xa0", " ") for a in certinfo[i].split(",")
                    ]
                }
            if "X509v3\xa0Authority\xa0Key\xa0Identifier:" in certinfo[i]:
                i += 1
                cert["extensions"]["authority_key_identifier"] = certinfo[i][
                    22:
                ].replace(":", "")
            if "X509v3\xa0Subject\xa0Key\xa0Identifier:" in certinfo[i]:
                i += 1
                cert["extensions"]["subject_key_identifier"] = certinfo[i][16:].replace(
                    ":", ""
                )
            if "Authority\xa0Information\xa0Access:" in certinfo[i]:
                cert["extensions"]["authority_information_access"] = {}
                i += 1
                while certinfo[i].startswith(
                    "\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0"
                ):
                    split = certinfo[i].split("\xa0-\xa0")
                    cert["extensions"]["authority_information_access"][
                        split[0].strip().replace("\xa0", " ")
                    ] = split[1].strip()
                    i += 1
                i -= 1
            # Warning : does not parse all the X509 extensions
            i += 1
        return cert
