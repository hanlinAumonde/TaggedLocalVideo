import {
  Component,
  computed,
  input,
  output,
} from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'app-pagination',
  standalone: true,
  imports: [MatButtonModule, MatIconModule],
  templateUrl: './pagination.html',
})
export class PaginationComponent {

  currentPage = input<number>(0);
  totalPages = input<number>(0);

  pageChanged = output<number>();

  isFirstPage = computed(() => this.currentPage() === 0);
  isLastPage = computed(() => this.currentPage() + 1 === this.totalPages());

  pages = computed(() => {
    const total = this.totalPages();
    const current = this.currentPage();

    if (total <= 3) {
      return Array.from({ length: total }, (_, i) => i + 1);
    }

    if (current === 0) {
      return [1, 2, 3];
    }

    if (current === total - 1) {
      return [total - 2, total - 1, total];
    }

    return [current, current + 1, current + 2];
  });

  changePage(page: number): void {
    if (page < 0 || page >= this.totalPages()) return;
    this.pageChanged.emit(page);
  }
}
