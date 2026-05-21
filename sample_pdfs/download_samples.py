import os
import urllib.request

SAMPLES = [
    {
        "filename": "lakeland_generator_spec.pdf",
        "url": "https://www.lakelandgov.net/media/19783/generator-specification-for-public-lift-stations-revised-2024-07-30-2024.pdf",
        "doc_type": "owner_spec",
        "description": "City of Lakeland — Generator Specification for Public Lift Stations (2024)",
    },
    {
        "filename": "caterpillar_3512b_spec.pdf",
        "url": "https://emc.cat.com/pubdirect.ashx?media_string_id=SS-10277269-1000028914-150.pdf",
        "doc_type": "vendor_submittal",
        "description": "Caterpillar 3512B — Technical Specification Sheet (1230 ekW, Continuous Rating)",
    },
]


def download_samples():
    out_dir = os.path.dirname(os.path.abspath(__file__))
    for s in SAMPLES:
        out_path = os.path.join(out_dir, s["filename"])
        if os.path.exists(out_path):
            print(f"  Already exists: {s['filename']}")
            continue
        print(f"  Downloading {s['filename']}...")
        try:
            urllib.request.urlretrieve(s["url"], out_path)
            print(f"  ✓ {s['filename']}")
        except Exception as e:
            print(f"  ✗ Failed: {e}. Download manually from: {s['url']}")

    casper_path = os.path.join(out_dir, "casper_college_generator_spec.pdf")
    if not os.path.exists(casper_path):
        print("""
  NOTE: The Casper College generator spec PDF needs to be sourced manually.
  Search: "Casper College package engine generator specification UL 508A"
  Or use any generator control panel specification that includes:
  UL 508A, UL 489, emergency stop, alarm contacts, fault historian requirements.
  Save as: sample_pdfs/casper_college_generator_spec.pdf
        """)


if __name__ == "__main__":
    download_samples()
