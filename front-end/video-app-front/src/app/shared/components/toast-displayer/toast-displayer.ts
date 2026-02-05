import { Component, inject } from '@angular/core';
import { ToastService } from '../../../services/toast-service/toast-service';
import { MatIconModule } from "@angular/material/icon";

@Component({
  selector: 'app-toast-displayer',
  imports: [MatIconModule],
  templateUrl: './toast-displayer.html',
})
export class ToastDisplayer {
  readonly toastService = inject(ToastService);
}
