# TurViz

TurViz reads and visualizes the tape history of a Turing machine.

## Installation and launch

The project uses [uv](https://docs.astral.sh/uv/).

```shell
uv sync
uv run turviz
```

## Desktop distributions

GitHub Actions can build native packages for Windows, macOS and Linux. The
workflow runs automatically for version tags such as `v0.1.0`, or manually
from the **Actions** tab with **Build desktop distributions**.

Each workflow run publishes these downloadable artifacts:

- `turviz-windows`: a ZIP containing `TurViz.exe`;
- `turviz-macos`: a ZIP containing the macOS application bundle;
- `turviz-linux`: a `.tar.gz` containing the Linux executable.

To publish a release:

```shell
git add .
git commit -m "Add multi-platform desktop build"
git tag v0.1.0
git push origin main --tags
```

The builds must run on their target operating system because PySide6 and Qt
include platform-specific native libraries. The workflow therefore uses one
GitHub Actions runner per operating system.

## Example machines

The `examples/` folder contains ready-to-open machines:

- `busy_beaver_3.tm`: a compact machine with a rich trace and a halt;
- `growing_triangle.tm`: builds a region of cells set to `1`;
- `two_state_cycle.tm`: a deliberately non-terminating cycle;
- `periodic_signal.tm`: a periodic pattern to explore with the step limit.

## `.tm` format

Each line starts with the state name, followed by the branch for symbol `0`
and the branch for symbol `1`. A normal branch contains three fields:
`write, move (L/R), next state`. A halt branch is simply `HALT` and contains no
additional fields.

Existing files remain valid: without directives, the first declared state is
the initial state. To make this explicit, a file can add these lines before its
transitions:

```text
@version 1
@initial START
```

`@version 1` declares the current format version and `@initial` lets you choose
any declared state as the starting point. Each directive is optional and may
appear only once; unknown directives are reported with their line number.

```text
A,1,R,B,0,L,B
B,HALT,1,R,A
```

Spaces around commas, blank lines and comments beginning with `#` are accepted.
The tape starts filled with `0`, with the head at position `0`. Execution stops
on `HALT`, a detected cycle, or when the step limit is reached.

## Exploring a machine

- The tape uses black for `0` and white for `1`.
- The head uses a distinct HSV hue for each state and is rendered with 50%
  transparency, so the underlying tape value remains visible.
- The lower panel contains a state table and a graph view with colored nodes,
  directed transitions and readable labels for dense graphs.
- After execution, the step slider and previous/next buttons let you inspect
  the trace progressively. The status bar shows the current state, head
  position and number of cells set to `1`.
- `Play` starts automatic playback; the interval is configurable in
  milliseconds and playback stops at the end.
- `Insights` reports the explored width, maximum width, maximum number of
  cells set to `1` and final number of cells set to `1`.
- The renderer is optimized for large traces: it paints the background once
  and draws only non-zero cells and head positions.

## Quick editing

The `Add state` button opens a guided form for both branches, with choices for
`HALT`, write value, movement and target state. `Ctrl+Enter` runs the machine
and `Ctrl+S` saves it.
