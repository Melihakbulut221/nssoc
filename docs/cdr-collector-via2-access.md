# Collector-driver access reinforcement from actual loaded evidence

Actual drainM23 loaded41430498959 was rejected with native engine exit0, and fullwave diagnosis41433864856 independently reproduced every gate. Actual collector path drops are30.27..94.18mV at the four failingHBT minima. Earlier emitter-path resistance reduction27.46..28.97percent did not close the electrical gates. Target the collector supply paths next.

The candidate targets ONLY original HBT54/56/106/108 emitter terminals driving the two native collector nets. It does not modify the four lower selector HBTs. Begin from exact GDS5e5ef394 and current freshRC41428920414; the complete source pins/archive acquisition and103original controls are unchanged. The new generator is added; all preexisting function ASTs except explicit main dispatch are identical to6a6b14ef4cb48666ce4ada1d89ba3796075389b2.

At each actual owned Metal2 terminal point, retain original four Via2 cuts. Proposed M3rectangle x±1825nm,y[-650,+450]nm around the actual5nm extraction point (originalHBT reference is exactly2nm above). Add12Via2cuts: eight at y-480nm,xoffset±1680/±1200/±720/±240 and four at y0,xoffset±1680/±1200. All190nm cuts,480nmpitch,50nmbothmetal enclosure,240nmoriginal/new spacing. Require EXACTLY12newcuts per4sites=48total; reject any unavailable site. New M3 must attach to ownedM3, remain withinextent, clear all foreignM3 by240nm and foreignadjacentvias by50nm. Actual old/newM2point ownership,4oldcuts/site,2nativecollector nets and all13conductorunions are mandatory.

OnlyVia2/M3 may change; verify serialized exactdelta and originalmaterial reversal. No device/primitive change. All source/geometry controls, full560DRC, deepflatLVS13, independentcanonical ownership, freshRC, unchanged full loadedwaves, via-current/EM and bias review remain required. No promise that this local change alone closes headroom, sampler delay or fullPHY.

The superseded8HBT drafting idea was never generated/dispatched. Current candidate uses only the four collector drivers selected from actual operating loss. All native work and waves remain GitHub-only.
