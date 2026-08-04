import hashlib, os
from PIL import Image

REVIEW_DIR = "outputs/canary-review/brief-1c6fd0618b67"

checksums = []
for f in sorted(os.listdir(REVIEW_DIR)):
    fp = os.path.join(REVIEW_DIR, f)
    if f.endswith(".sha256"):
        continue
    h = hashlib.sha256(open(fp, "rb").read()).hexdigest()
    checksums.append("%s  %s" % (h, f))
    sz = os.path.getsize(fp)
    dims = "N/A"
    if f.endswith(".png"):
        try:
            img = Image.open(fp)
            dims = "%dx%d" % img.size
        except Exception:
            pass
    print("  %s -- %d bytes -- %s -- %s" % (f, sz, dims, h[:16]))

with open("%s/checksums.sha256" % REVIEW_DIR, "w") as out:
    out.write("\n".join(checksums) + "\n")

print("\nChecksums regenerated.")
