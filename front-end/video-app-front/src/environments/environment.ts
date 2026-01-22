export const environment = {
    production: true,
    backend_api: "",
    video_stream_api: "/video/stream/",
    homepage_api: "/home",
    searchpage_api: "/search",
    management_api: "/management",
    videopage_api: "/video",
    pageListSize: 5,
    refreshKey: "_refresh_key",
    scrollKey: "_scroll_position",
    rootMainContainerId: "root-main-container",
    VALIDATION_RULES:{
        NAME_MAX_LENGTH: 200,
        AUTHOR_MAX_LENGTH: 50,
        INTRODUCTION_MAX_LENGTH: 2000,
        TAG_MAX_LENGTH: 30,
        MAX_TAGS_COUNT: 50,
        PAGE_NUMBER_MIN: 1,
        PAGE_NUMBER_MAX: 10000,
    },
    ERROR_TOAST_SETTINGS: {
        MAX_TOASTS: 4,
        AUTO_DISMISS_MS: 10000,
        EXIT_ANIMATION_MS: 300,
    }
} as const;