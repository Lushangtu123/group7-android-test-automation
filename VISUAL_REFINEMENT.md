# Light presentation skin

The live workbench now uses the earlier Automation Studio palette: warm paper, forest-green controls, restrained borders, and serif display text. The log pane retains a dark terminal surface. Continuous device capture, Appium execution, validation, current-turn matching, logging and export behavior are unchanged.

Only `static/index.html` (header branding) and `static/style.css` changed. Backend Python and browser JavaScript hashes were checked against the previous delivery. Existing runtime evidence bytes were checked after browser inspection. No additional Android tests were executed for this visual-only revision.

Historical live acceptance results retain their actual original source snapshots and original dark interface screenshots. They are not presented as execution of this newer skin. New screenshots in `verification/refined_*.png` document the light interface in idle or explicitly selected completed-result states.

The earlier `Group7_Live_Demo.zip` is preserved. `Group7_Live_Demo_Presentation.zip` is a separate updated distribution. Its source mapping and checksum manifest describe its own bytes. The previous visual sources are also retained in the `visual_before_*` verification folder.

Open or refresh http://127.0.0.1:8770/ to see the revised skin. Click Start real demo when you want to execute the actual Android tests.
