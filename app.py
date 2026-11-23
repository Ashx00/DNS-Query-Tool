from flask import Flask, render_template, request, make_response
import dns.resolver
import time
import csv
import io
import re

app = Flask(__name__)

DNS_RECORDS = ["A", "AAAA", "MX", "NS", "CNAME", "TXT"]


def get_dns_records(domain):
    results = {}

    for record_type in DNS_RECORDS:
        try:
            answers = dns.resolver.resolve(
                domain,
                record_type,
                lifetime=3
            )

            records = []

            for answer in answers:
                if record_type == "MX":
                    records.append(
                        f"Priority: {answer.preference}, "
                        f"Mail Server: {answer.exchange}"
                    )
                else:
                    records.append(str(answer))

            results[record_type] = {
                "records": records,
                "status": "Success"
            }

        except dns.resolver.NXDOMAIN:
            results[record_type] = {
                "records": [],
                "status": "Domain does not exist"
            }

        except dns.resolver.NoAnswer:
            results[record_type] = {
                "records": [],
                "status": "No records found"
            }

        except Exception:
            results[record_type] = {
                "records": [],
                "status": "Query failed or timed out"
            }

    return results


@app.route("/", methods=["GET", "POST"])
def home():
    results = None
    domain = ""
    lookup_time = None

    if request.method == "POST":
        domain = request.form.get("domain", "").strip()

    if domain:
        import re

        pattern = r"^(?=.{1,253}$)(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,63}\.?$"

        if not re.match(pattern, domain):
            results = {
                "ERROR": {
                    "records": [],
                    "status": "Please enter a valid domain name."
                }
            }
        else:
            start_time = time.perf_counter()

            results = get_dns_records(domain)

            end_time = time.perf_counter()
            lookup_time = round(
                (end_time - start_time) * 1000, 2
            )

            
    return render_template(
        "index.html",
        results=results,
        domain=domain,
        lookup_time=lookup_time
    )


@app.route("/export", methods=["POST"])
def export_csv():

    domain = request.form.get("domain", "").strip()

    pattern = r"^(?=.{1,253}$)(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,63}\.?$"

    if not re.fullmatch(pattern, domain):
        return "Invalid domain name", 400

    # Retrieve DNS records again
    results = get_dns_records(domain)

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # CSV headings
    writer.writerow([
        "Domain",
        "Record Type",
        "Status",
        "DNS Result"
    ])

    # Add DNS results
    for record_type, data in results.items():

        if data["records"]:
            for record in data["records"]:
                writer.writerow([
                    domain,
                    record_type,
                    data["status"],
                    record
                ])

        else:
            writer.writerow([
                domain,
                record_type,
                data["status"],
                "No data"
            ])

    # Send CSV file to browser
    response = make_response(output.getvalue())

    response.headers["Content-Disposition"] = (
        f"attachment; filename={domain}_DNS_Report.csv"
    )

    response.headers["Content-Type"] = "text/csv"

    return response

if __name__ == "__main__":
    app.run(debug=True)
