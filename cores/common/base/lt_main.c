/* Copyright (c) Kuba Szczodrzyński 2022-06-19. */

#include <libretiny.h>

#include <fal.h>

fal_partition_t fal_root_part = NULL;

// Initialize C library
void __libc_init_array(void);
// Main app entrypoint
int main(void);

int lt_main(void) {
	// early initialize the family and variant
	lt_init_family();
	lt_init_variant();
	// print a startup banner
	LT_BANNER();
	// log the compile timestamp; kept out of LT_BANNER_STR (see libretiny.h)
	// so only this one file is rebuilt when the time changes; uses LT_LOG
	// directly, like LT_BANNER(), so it prints regardless of LT_LOGLEVEL
	LT_LOG(LT_LEVEL_INFO, __FUNCTION__, __LINE__, "Compiled at " __DATE__ " " __TIME__);
	// initialize C library
	__libc_init_array();
	// inform about the reset reason
	LT_I("Reset reason: %s", lt_get_reboot_reason_name(0));
	// initialize FAL
	fal_init();
	// provide root partition
	fal_root_part = (fal_partition_t)fal_partition_find("root");

	// run the application
	return main();
}
