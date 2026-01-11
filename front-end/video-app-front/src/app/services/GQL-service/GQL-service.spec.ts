import { TestBed } from '@angular/core/testing';

import { GqlService } from './GQL-service';

describe('InputConstructor', () => {
  let service: GqlService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(GqlService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
