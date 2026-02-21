import { Component, computed, effect, inject, input, signal } from '@angular/core';
import { ToastService } from '../../../services/toast-service/toast.service';
import { MatIconModule } from "@angular/material/icon";
import { Toast } from '../../models/toast.model';

@Component({
  selector: 'app-toast-displayer',
  imports: [MatIconModule],
  templateUrl: './toast-displayer.html',
})
export class ToastDisplayer {
  readonly toastService = inject(ToastService);

  toasts = this.toastService.toasts;
}
