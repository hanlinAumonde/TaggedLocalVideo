import { TestBed } from '@angular/core/testing';

import { PathHistoryService } from './path-history.service';

describe('PathHistoryService', () => {
    let service: PathHistoryService;
    
    beforeEach(() => {
        TestBed.configureTestingModule({});
        service = TestBed.inject(PathHistoryService);
    });

    it('should be created', () => {
        expect(service).toBeTruthy();
    });
});

