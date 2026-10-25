# Power128 TX: first saved-process continuations

Normal run39630182787 and swapped-leaf-select run39630188922 both restored their exact original power128 native capsules and retained a single native entrypoint. After3600 host seconds, normal reached4.798637531ns with10423 complete rows; the fault case reached4.827412540ns with10484 complete rows. Both retained all14182 native columns and actual partial rows. Original protected sources remained unchanged.

These are saved-process progress results, not full34ns capture or electrical acceptance. Both immutable capsules and raw prefixes are retained. The next continuation uses7200 host seconds, already supported by the unchanged controller and within the existing180-minute job limit. This changes only the host segment length; simulator state, original34ns capture, stimuli, models, timestep and acceptance gates are unchanged.

Mainchip input preparation already passed. The completed-route review's first input preflight exposed a shared-reader output-directory error before native analysis; the failure remains published, and the binding fix is under real hosted verification.
