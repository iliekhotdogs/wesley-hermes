# Equation and Chart PDF Verification

## Retrieve and identify

For a Drive sharing link, use `google-workspace` metadata lookup and download by its exact file ID. Confirm the returned filename rather than substituting a similarly named sample or generated study document. Extract the downloaded PDF to locate all substantive pages; blank work pages do not require visual processing.

## Render relevant pages

Use an interpreter with PyMuPDF installed. Prefer `import pymupdf`; the legacy `fitz` alias may emit a deprecation warning. Supply explicit input and output paths in the managed scratch workspace.

```python
from pathlib import Path
import pymupdf

source = Path("<downloaded-pdf-path>")
out = Path("<scratch-directory>")
out.mkdir(parents=True, exist_ok=True)
doc = pymupdf.open(source)
page_numbers = [3, 4]  # One-based pages selected after text extraction.
for number in page_numbers:
    page = doc[number - 1]
    target = out / f"document-page-{number}.png"
    page.get_pixmap(matrix=pymupdf.Matrix(1.7, 1.7)).save(target)
    print(target)
```

Inspect the resulting images with `vision_analyze`; batch independent page inspections. Zoom or re-render a region when an exponent, prime, fraction, or axis tick remains ambiguous. This workflow also applies when the PDF has a usable text layer but its mathematical extraction is malformed.

## Transcribe, then calculate

- Check the entire exponent and fraction grouping visually: `2^(10 - t/3)` is different from `2^10 - t/3`.
- Read the option label together with its mathematical expression; extracting the correct expression alone does not establish its multiple-choice letter. Simplify the other options too: a quotient and its expanded form may be equivalent. If multiple options are correct, name all of them and flag the source ambiguity.
- Inspect a graph directly for turning points, concavity changes, axes, and displayed extent. Extracted axis labels alone do not describe the curve.
- Verify transcribed expressions with a calculator or symbolic tool. For isolated SymPy verification without changing the active environment, use `uv run --with sympy python <verification-script.py>`.
- For closed-interval extrema, compare endpoints and interior critical points. For inflections, check a concavity sign change rather than accepting every zero of the second derivative.
- Retain exact expressions where appropriate, add units to interpreted rates, and explicitly mark graphical estimates as approximate.
- Use `fractions.Fraction` for exact rational evaluations when a symbolic package is unnecessary; construct values with `Fraction(numerator, denominator)` rather than from an already-rounded float.
- Distinguish an inconclusive second-derivative test from a classification: if the second derivative vanishes, check derivative or concavity signs before calling the point an extremum or stationary inflection.

## Deliver and verify a requested graph

1. Compute and verify endpoints, critical points, and inflection points from the visually confirmed formula. Preserve rational coordinates in labels even if sampling uses floats.
2. Plot the stated domain and label the requested features. Add a separately scaled detail panel when the full-range vertical scale makes nearby features indistinguishable; label that panel as a detail view so its scale is not mistaken for the main graph.
3. Use the available plotting stack. For a simple function plot, an SVG polyline with axes, tick labels, and point annotations can be rasterized with PyMuPDF without introducing a plotting dependency:

```python
from pathlib import Path
import pymupdf

# svg_text is a complete SVG with an explicit width, height, and viewBox.
# Map data to pixel coordinates before generating the polyline and labels.
output = Path("<scratch-directory>") / "function-graph.png"
doc = pymupdf.open(stream=svg_text.encode("utf-8"), filetype="svg")
doc[0].get_pixmap(matrix=pymupdf.Matrix(1.4, 1.4)).save(output)
```

4. Open the actual PNG with `vision_analyze` and inspect readable labels, curve shape, clipping, and overlap. Assertions about file existence or dimensions alone cannot establish visual correctness.
5. If code was written, run the generator and a focused check of exact feature values, required labels, image dimensions, and nonblank pixels. Report this as ad-hoc verification, not a full test-suite pass. Attach the rendered graph alongside the numbered answers.
