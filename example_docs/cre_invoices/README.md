# Sample Commercial Real Estate Invoices

These two PDFs are the sample invoices the PDF intake is tested against. Open
them in any PDF viewer to see exactly what the intake reads.

Both invoices are billed for the **same lease** (invoice `INV-2024-0042`,
tenant Acme Retail LLC, Harbor Point Tower, Suite 1200). Our recorded ground
truth for that lease expects:

| Charge                  | Expected amount |
| ----------------------- | --------------: |
| Base Rent               |     $20,833.33  |
| Common Area Maintenance |      $5,000.00  |
| Real Estate Tax Recovery|      $1,250.00  |
| **Total Amount Due**    |  **$27,083.33** |

### `positive_invoice_matches_ground_truth.pdf`

What a correct invoice looks like. Every charge matches the lease, so the intake
reconciles it as **matched** - no action needed.

### `negative_invoice_overcharged_cam.pdf`

The same invoice, but the landlord has overstated **Common Area Maintenance** by
$750 (billing $5,750.00 instead of $5,000.00), which inflates the total to
$27,833.33. The intake reconciles it as a **discrepancy**, flagging the CAM line
and the total so the bill can be disputed before payment.

These files are generated from `tests/intake/realistic_invoice.py`. To
regenerate them after a change, run:

```sh
python -m tests.intake.realistic_invoice
```
