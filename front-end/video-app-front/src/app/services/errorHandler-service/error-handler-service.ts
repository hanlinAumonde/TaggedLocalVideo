import { Injectable, signal } from '@angular/core';
import { environment } from '../../../environments/environment';
import { ErrorToast } from '../../shared/models/error-toast.model';

@Injectable({
  providedIn: 'root',
})
export class ErrorHandlerService {
  private counter = 0;

  private _toasts = signal<ErrorToast[]>([]);
  toasts = this._toasts.asReadonly();

  emitError(message: string) {
    const id = ++this.counter;

    this._toasts.update(list => {
      const newList = [...list, { id, message }];
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
