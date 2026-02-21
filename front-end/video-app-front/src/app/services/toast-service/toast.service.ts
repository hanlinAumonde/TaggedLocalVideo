import { Injectable, signal } from '@angular/core';
import { environment } from '../../../environments/environment';
import { Toast } from '../../shared/models/toast.model';

@Injectable({
  providedIn: 'root',
})
export class ToastService {
  private counter = 0;

  private _toasts = signal<Toast[]>([]);
  toasts = this._toasts.asReadonly();

  emitErrorOrWarning(message: string, type: 'error' | 'warning' = 'error', beyondDialog: boolean = false) {
    const id = ++this.counter;

    const updateFn = this._toasts.update;

    updateFn(list => {
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
    const updateFn = this._toasts.update;
    // marked as removing to trigger exit animation
    updateFn(list =>
      list.map(t => (t.id === id ? { ...t, removing: true } : t))
    );
    // remove after animation ends
    setTimeout(() => this.removeToast(id), environment.ERROR_TOAST_SETTINGS.EXIT_ANIMATION_MS);
  }

  private removeToast(id: number) {
    const updateFn = this._toasts.update;
    updateFn(list => list.filter(t => t.id !== id));
  }

  public clearAllToasts() {
    this._toasts().forEach(t => {
      this.removeToast(t.id);
    });
  }
}
