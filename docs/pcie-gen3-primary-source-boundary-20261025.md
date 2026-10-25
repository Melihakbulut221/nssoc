# Gen3 target-source boundary after complete-record transport

The source audit records the target standard catalog, its errata catalog, and three public PCI-SIG clarifications relevant to the future training owner. This is a source boundary, not a conformance result. [PCI-SIG lists Base Revision3.0](https://pcisig.com/PCIExpress/Specs/Base/_3.0); its download redirected to the member login in this review. The normative document and target errata were not read.

The [public equalization FAQ](https://pcisig.com/faq?field_category_value%5B%5D=pci_express_3.0&keys=equalization) supplies the narrow requirements in the accompanying JSON. Neither the existing 16-symbol collector nor its proposed recovered-clock CDC implements those stateful rules. Their lossless record/flag proofs must not be reported as training-set acceptance, negotiated x4 operation, or link-up.

The [official catalog](https://pcisig.com/specification-overview/pci-express-base) separately lists the 2014-10-23 Base3.0 errata. Earlier Gen1/2 references cannot establish all later encoding, equalization, timer or recovery rules. The next owner implementation needs an independently reviewed target oracle. Analog return-path diagnosis, CDR extraction and main-chip routing continue independently; no completion criterion has changed.
