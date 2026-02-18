import { Component, computed, ElementRef, input, OnChanges, output, signal, viewChild } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';
import { environment } from '../../../../environments/environment';

@Component({
  selector: 'app-bottom-toolbar',
  imports: [MatIconModule],
  templateUrl: './bottom-toolbar.html'
})
export class BottomToolbar {
  currentPath = input.required<string[]>();
  hasSelection = input.required<boolean>();
  selectedCount = input.required<number>();
  isAtRoot = input.required<boolean>();
  tableWidth = input.required<number>();

  batchOperation = output<void>();
  navigateBack = output<void>();
  navigateToPath = output<string[]>();

  paths = computed(() => {
    return ["Root", ...this.currentPath()];
  });

  toolbarVisible = signal<boolean>(true);

  toggleToolbar() {
    this.toolbarVisible.update(v => !v);
  }

  navigatePath(index: number){
    if(index < 0 || index > this.currentPath().length) return;
    if(index === this.currentPath().length) return;
    const targetPath = this.currentPath().slice(0, index);
    this.navigateToPath.emit(targetPath);
  }
}
