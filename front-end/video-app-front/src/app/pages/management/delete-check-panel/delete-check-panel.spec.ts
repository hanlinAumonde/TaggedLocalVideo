import { ComponentFixture, TestBed } from '@angular/core/testing';

import { DeleteCheckPanel } from './delete-check-panel';

describe('DeleteCheckPanel', () => {
  let component: DeleteCheckPanel;
  let fixture: ComponentFixture<DeleteCheckPanel>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DeleteCheckPanel]
    })
    .compileComponents();

    fixture = TestBed.createComponent(DeleteCheckPanel);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
