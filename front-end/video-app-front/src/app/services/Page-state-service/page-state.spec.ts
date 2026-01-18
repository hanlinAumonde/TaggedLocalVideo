import { TestBed } from '@angular/core/testing';

import { PageState } from './page-state';

describe('PageState', () => {
  let service: PageState;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(PageState);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
