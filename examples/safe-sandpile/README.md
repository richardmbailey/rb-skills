# Safe-pipeline sandpile benchmark

This small web application simulates grains accumulating on a square platform. It offers a physical slope pile for forming a tall heap at a chosen angle of repose and the classic Bak–Tang–Wiesenfeld critical sandpile for comparison. Material crossing the open edge leaves the platform. The application measures the relaxation caused by every added grain and compares avalanche size with observed frequency.

Python owns the simulation, analysis, and loopback-only HTTP server. The browser supplies controls and renders the lattice, an isometric relief view looking down at approximately 40 degrees, and the charts. The application uses only the Python standard library and local files.

The grain-source control offers uniform random drops across the platform or a central source with configurable spatial jitter. The jitter value is an integer radius in lattice cells. Within that radius, positions are drawn from a seeded, centre-weighted discrete Gaussian distribution and are clipped to the circular footprint and platform; a radius of zero always selects the exact middle cell. A source or jitter change applies to the next batch without resetting the current lattice or its measurements.

## Simulation models

The default **Physical slope pile** stores an unrestricted number of grain layers at each site. One layer is 0.1 horizontal cell widths high. After each addition, every occupied site compares its height with all eight neighbours. Diagonal distances are corrected by a factor of square root two. A site moves one layer towards a seeded choice among its steepest downhill directions whenever the physical slope exceeds the selected angle of repose. These moves occur in parallel waves until the complete surface is stable. An outside neighbour has zero height, so material eventually crosses the platform edge and is recorded as lost mass.

The layer resolution makes the result an approximation: a requested 40-degree angle normally produces a steepest stable adjacent-cell slope of about 38.7 degrees. A finer layer would approach the target more closely but would require more simulated grains and relaxation work to create the same physical height.

The optional **Critical sandpile (BTW)** retains the original threshold-four model. A site topples as soon as it reaches four grains, passing one grain to each orthogonal neighbour. Every relaxed BTW site is therefore limited to zero through three grains. Its three-dimensional view exaggerates those states for readability. This mode is useful for the classic self-organised-criticality experiment, but it is not a geometrically realistic heap.

Changing the simulation model or angle resets the experiment because the two modes assign different physical meanings to their height values and avalanche events. The physical view uses the documented layer thickness; only the BTW view is vertically exaggerated.

## Run the application

From this directory, run:

```bash
python3 -m sandpile.server --port 8000
```

Then open <http://127.0.0.1:8000>. Stop the server with `Ctrl-C`.

The server binds only to `127.0.0.1`. It does not make external requests. A single API step is limited to 5,000 grains, and the grid is limited to 128 by 128 sites.

## Measurements

For every added grain, the model records:

- avalanche size: the total number of BTW topplings or physical one-layer moves;
- avalanche area: the number of distinct sites that toppled or moved material;
- avalanche duration: the number of parallel relaxation waves; and
- mass lost: grains that crossed the platform boundary.

The interface also reports maximum height in grain layers and the steepest local physical slope. It shows the raw positive-avalanche frequency and complementary cumulative distribution on logarithmic axes, along with an approximate discrete maximum-likelihood exponent above a user-selected `xmin` and a descriptive Kolmogorov–Smirnov distance. These are exploratory diagnostics. They do not establish that the observations follow a power law. Results from the physical and BTW modes use different event definitions and must not be pooled or compared as if they came from the same model. A defensible statistical claim would require uncertainty estimates, principled threshold selection, and comparison with alternative heavy-tailed distributions.

The model checks the exact identity:

```text
grains added = mass retained on the grid + mass lost at the boundary
```

The displayed mass-balance residual should always be zero.

## Test and benchmark commands

Run the behavioural test suite:

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
```

Run the repeatable scientific benchmark:

```bash
python3 tests/run_scientific_benchmark.py --burn-in 5000 --samples 20000
```

The benchmark currently exercises the classic BTW model. It emits JSON containing per-run conservation checks, compact avalanche summaries, logarithmic bins, and throughput. It omits the potentially very large raw frequency and CCDF tables. It uses several fixed seeds and grid sizes so later runs can be compared. Runtime depends on the machine and selected sample count.

## Reproducibility boundaries

Python's seeded pseudo-random generator controls uniform drops, central jitter, and equal-slope tie-breaking. A complete run is repeatable for the same implementation, model, grid, seed, source, jitter, angle, and addition sequence. The BTW toppling rule is Abelian, so its fully relaxed final state does not depend on the legal toppling order, although the reported parallel-wave duration depends on the chosen wave definition. The physical slope model is a synchronous cellular approximation rather than a discrete-element simulation of individual grain shapes, friction, momentum, packing, or air effects. Its selected tie-breaking and parallel-update rules are part of the model and can affect the detailed surface and event sequence. Browser drawing speed does not affect either simulation because the server completes each batch before returning the new state.
