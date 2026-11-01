# Original-master q15 loaded transfer diagnosis

This reads the complete existing native wave from run41277054717, sourcee85179e6900c2be9d931a8b30549c99f47c7617d, release430382305. No additional simulator or geometry mutation runs. Native payload remains only on GitHub.

The original124HBT/all6stage/1530delay/phaseVI reproduction and simultaneous operating points remain unchanged. Seven frozen-reader, thirteen event and seven transfer controls must pass before archive acquisition.

Four authenticated paths are traced: A->AD, C->CD, B->S0 and B->S1. Each receiver base must have one native series resistor, one parallel MIM and one actual avss shunt from its assigned sampler collector. All500native devices and receiver terminal identities are preserved. Shared B divider nodes and distinct routed receiver leaves are retained.

A hysteretic crossing detector uses50mV for sampler/buffer observations and10mV for internal bases. These are diagnostic noise thresholds, not altered external acceptance gates. A causal match requires exactly one same-direction crossing before the next input transition and within125ps. Missing/ambiguous and preceding/following same-direction events are retained; the tool does not infer a successful transfer from unmatched or ambiguous edges.

The unchanged electrical screen still requires100mV/37.5ps sampler and100mV/75ps XOR validity. This diagnosis cannot establish circuit acceptance, freshPEX, closed-loop/fullPHY operation or finalchip timing. The complete events and topology are published as derived JSON.
