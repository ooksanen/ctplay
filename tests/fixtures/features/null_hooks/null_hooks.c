/* Test only: handlers that change nothing. */
#include "slim.h"

int null_on_button(void *ctrl, uint32_t id, uint32_t *ret)
{
    (void)ctrl;
    (void)id;
    (void)ret;
    return SLIM_PASS;
}

void null_on_leds(void *ctrl, uint16_t *out)
{
    (void)ctrl;
    (void)out;
}
