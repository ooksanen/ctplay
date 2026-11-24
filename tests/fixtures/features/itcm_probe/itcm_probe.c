/* Test only: ITCM data placed by the build, zeroed and write-tested by the runtime, set by init(). */
#include "slim.h"

uint32_t probe_itcm[2] SLIM_ITCM(probe_itcm);

void probe_init(void)
{
    probe_itcm[0] = 0xC0FFEE01u;
}

void probe_on_leds(void *ctrl, uint16_t *out)
{
    (void)ctrl;
    (void)out;
}
