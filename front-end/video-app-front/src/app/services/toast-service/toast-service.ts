import { inject, Injectable, signal } from '@angular/core';
import { environment } from '../../../environments/environment';
import { Toast } from '../../shared/models/toast.model';
import { Overlay } from '@angular/cdk/overlay';
import { ToastDisplayer } from '../../shared/components/toast-displayer/toast-displayer';
import { ComponentPortal } from '@angular/cdk/portal';

@Injectable({
  providedIn: 'root',
})
export class ToastService {
  private overlay = inject(Overlay);
  private counter = 0;

  private _toasts = signal<Toast[]>([]);
  toasts = this._toasts.asReadonly();

  emitErrorOrWarning(message: string, type: 'error' | 'warning' = 'error') {
    const id = ++this.counter;

    this._toasts.update(list => {
      const newList = [...list, { id, message, type }];
      // when exceeding max toasts, remove the oldest one
      if (newList.length > environment.ERROR_TOAST_SETTINGS.MAX_TOASTS) {
        const oldest = newList.find(t => !t.removing);
        if (oldest) {
          oldest.removing = true;
          setTimeout(() => this.removeToast(oldest.id), environment.ERROR_TOAST_SETTINGS.EXIT_ANIMATION_MS);
        }
      }
      return newList;
    });

    // close automatically after a delay
    setTimeout(() => this.dismiss(id), environment.ERROR_TOAST_SETTINGS.AUTO_DISMISS_MS);
  }

  dismiss(id: number) {
    // marked as removing to trigger exit animation
    this._toasts.update(list =>
      list.map(t => (t.id === id ? { ...t, removing: true } : t))
    );
    // remove after animation ends
    setTimeout(() => this.removeToast(id), environment.ERROR_TOAST_SETTINGS.EXIT_ANIMATION_MS);
  }

  private removeToast(id: number) {
    this._toasts.update(list => list.filter(t => t.id !== id));
  }
}
