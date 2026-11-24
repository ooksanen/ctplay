"""q1_mono_order: route (a) with mono record on, a falling triad with bass (send order G E C(root) bass; the heartbeat's
note-offs: notes[] first (G E bass), the root last). Medium (2 ticks): the root lands on step 7, the bass on step 8;
the root commits after the bass, so mono's visit (step 8) does not hold it and its commit clears step 7's other
units: the roll's own G and E there. Slow (4 ticks): root on 8, bass on 9: nothing of the roll lost."""
from q1_route_a import case

for sp in (2, 1):
    h, r = case(f"mono written q on {'medium' if sp == 2 else 'slow'} falling triad + bass", "written", sp, True, True,
                shape=1, bass=1, mono=True)
    print("        commit order:", [c["note"] for c in h.commits])
