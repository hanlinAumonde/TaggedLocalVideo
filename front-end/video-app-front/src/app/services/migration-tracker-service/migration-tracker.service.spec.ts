import { TestBed } from '@angular/core/testing';

import { MigrationTrackerService } from './migration-tracker.service';

describe('MigrationTrackerService', () => {
  let service: MigrationTrackerService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(MigrationTrackerService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
