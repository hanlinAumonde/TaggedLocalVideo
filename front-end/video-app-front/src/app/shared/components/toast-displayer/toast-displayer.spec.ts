import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ToastDisplayer } from './toast-displayer';

describe('ToastDisplayer', () => {
  let component: ToastDisplayer;
  let fixture: ComponentFixture<ToastDisplayer>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ToastDisplayer]
    })
    .compileComponents();

    fixture = TestBed.createComponent(ToastDisplayer);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
