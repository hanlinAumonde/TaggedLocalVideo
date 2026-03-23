import { TestBed } from "@angular/core/testing";

import { VideoUpdateEventService } from "./video-update-event.service";

describe("VideoUpdateEventService", () => {
    let service: VideoUpdateEventService;

    beforeEach(() => {
        TestBed.configureTestingModule({});
        service = TestBed.inject(VideoUpdateEventService);
    });

    it("should be created", () => {
        expect(service).toBeTruthy();
    })
});