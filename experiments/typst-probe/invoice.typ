#set page(paper: "us-letter", margin: (x: 0.8in, y: 0.6in))
#set text(font: "Latin Modern Sans", size: 10pt, fill: rgb("153744"))
#set par(leading: 0.5em)
#set document(title: "Invoice INV-2026-014", author: "Northstar Creative Studio", date: none)
#let muted = rgb("58737D")
#let label(body) = text(size: 8pt, weight: "bold", fill: muted, body)
#grid(columns: (1fr, 1fr), align: (left, right),
  image("logo.svg", width: 3.1in),
  [#text(size: 32pt, weight: "bold")[INVOICE] \ #text(fill: muted)[INV-2026-014]],
)
#v(20pt)
#line(length: 100%, stroke: 0.8pt + rgb("DDE7E9"))
#v(12pt)
#grid(columns: (1fr, 1fr, 0.75fr), gutter: 15pt,
  [#label[FROM] \ *Northstar Creative Studio* \ 125 Harbor Avenue, Suite 200 \ Seattle, WA 98101 \ hello\@northstar.example],
  [#label[BILL TO] \ *Willow & Pine Co.* \ 240 Market Street \ Portland, OR 97205 \ billing\@willowpine.example],
  [#label[ISSUED] \ September 29, 2026 \ #label[DUE DATE] \ October 13, 2026 \ #label[TERMS] Net 14],
)
#v(24pt)
#label[PROJECT] \
#text(size: 12pt, weight: "bold")[Brand refresh & website launch] \
#text(fill: muted)[Design and development services for September 2026.]
#v(16pt)
#table(columns: (1fr, auto, auto, auto), align: (left, right, right, right), inset: (x: 4pt, y: 9pt), stroke: none,
 table.header(label[DESCRIPTION], label[HOURS], label[RATE], label[AMOUNT]),
 table.hline(stroke: 0.5pt + muted),
 [*Product design* \ #text(size: 9pt, fill: muted)[Visual direction, layouts, and component design]], [24], [\$125.00], [\$3,000.00],
 [*Website development* \ #text(size: 9pt, fill: muted)[Responsive implementation and integrations]], [16], [\$150.00], [\$2,400.00],
 [*Quality assurance* \ #text(size: 9pt, fill: muted)[Browser testing and launch review]], [6], [\$100.00], [\$600.00],
 table.hline(stroke: 0.5pt + muted),
)
#align(right, table(columns: (1.4in, 1in), align: (left, right), stroke: none, inset: 4pt,
 [Subtotal], [\$6,000.00], [Tax], [\$0.00], [Paid to date], [\$0.00]))
#v(12pt)
#block(width: 100%, fill: rgb("EFF6F5"), inset: 14pt)[
 #grid(columns: (1fr, auto), align: (left, right),
 [#label[AMOUNT DUE] \ Due October 13, 2026 | USD],
 text(size: 27pt, weight: "bold", fill: rgb("187B6A"))[\$6,000.00])
]
#v(1fr)
#label[PAYMENT DETAILS] \
Please use the payment instructions supplied with your agreement. \
Include *INV-2026-014* as your payment reference.
#v(12pt)
#line(length: 100%, stroke: 0.8pt + rgb("DDE7E9"))
#grid(columns: (1fr, auto), [*Thank you for your business.*], [northstar.example])
#text(size: 8pt, fill: muted)[Sample invoice. All company and billing details are fictional.]
