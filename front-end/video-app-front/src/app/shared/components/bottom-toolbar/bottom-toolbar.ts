import { Component, input, output, signal } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'app-bottom-toolbar',
  imports: [MatIconModule],
  templateUrl: './bottom-toolbar.html'
})
export class BottomToolbar {
  currentPathDisplay = input.required<string>();
  hasSelection = input.required<boolean>();
  selectedCount = input.required<number>();
  isAtRoot = input.required<boolean>();

  batchOperation = output<void>();
  navigateBack = output<void>();

  toolbarVisible = signal<boolean>(false);

  toggleToolbar() {
    this.toolbarVisible.update(v => !v);
  }
}
