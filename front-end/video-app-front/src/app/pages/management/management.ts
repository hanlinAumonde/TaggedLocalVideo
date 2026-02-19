import { Component, inject, signal, computed, effect } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { GqlService } from '../../services/GQL-service/GQL.service';
import {
  BrowseDirectoryDetail,
  FileBrowseNode,
} from '../../shared/models/GQL-result.model';
import { PageStateService } from '../../services/Page-state-service/page-state.service';
import { environment } from '../../../environments/environment';
import { 
  SortCriterion, 
  ItemsSortOption, 
  ManagementRefreshState, 
  comparatorBySortOption 
} from '../../shared/models/management.model';
import { BottomToolbar } from '../../shared/components/bottom-toolbar/bottom-toolbar';
import { FileBrowseTable } from '../../shared/components/file-browse-table/file-browse-table';
import { ToastService } from '../../services/toast-service/toast.service';
import { PathHistoryService } from '../../services/path-history-service/path-history.service';

@Component({
  selector: 'app-management',
  imports: [
    BottomToolbar,
    FileBrowseTable
  ],
  templateUrl: './management.html'
})
export class Management {
  private gqlService = inject(GqlService);
  private dialog = inject(MatDialog);
  private stateService = inject(PageStateService);
  private toastService = inject(ToastService);
  
  pathHistoryService = inject(PathHistoryService)

  tableWidth = signal<number>(0);
  // true for ascending, false for descending
  sortCriteria = signal<SortCriterion>({
    index: 0,
    order: true
  });
  currentPath = signal<string[]>([]);
  directoryContents = signal(this.gqlService.initialSignalData<BrowseDirectoryDetail>([]));
  selectedIds = signal<Set<string>>(new Set());

  isAtRoot = computed(() => this.currentPath().length === 0);
  selectedCount = computed(() => this.selectedIds().size);
  hasSelection = computed(() => this.selectedIds().size > 0);

  constructor() {
    const hasStatePredicate = (state: string[] | undefined) =>
      state && Array.isArray(state);

    const state = this.stateService.getState<string[]>(
      environment.management_api + environment.refreshKey,
      false
    );

    if (hasStatePredicate(state)) {
      this.currentPath.set(state!);
    }

    this.setRefreshState();

    // Load directory when path changes
    effect(() => {
      const path = this.currentPath();
      this.stateService.setState(
        environment.management_api + environment.refreshKey,
        path,
        false
      );
      this.loadDirectory(path.length > 0 ? path.join('/') : undefined);
    });
  }

  // ─── Directory Data Loading ────────────────────────────────────────

  private loadDirectory(relativePath?: string, refreshCache: boolean = false) {
    this.gqlService.browseDirectoryQuery(relativePath, refreshCache).subscribe({
      next: (result) => {
        // Sometimes this condition can be true twice in a single request, because of the cache update after the request
        // So for the second time, newState will be undefined, and we shoudn't apply the sorting and scrolling again
        if(!result.loading && result.data) {
          const newState = this.stateService.getState<ManagementRefreshState>(
            environment.management_api + environment.refreshKey + environment.scrollKey,
            false
          );
          if(newState?.sortCriteria){
            this.sortCriteria.set(newState.sortCriteria);
            this.sortItemsBy(this.sortCriteria().index, result.data);
            this.directoryContents.set({...this.directoryContents(), loading: result.loading, error: result.error});
            setTimeout(() => {
              if(newState !== undefined){
                this.scrollTo(newState.scrollPosition);
              }
            }, 200);
          }
        }else{
          this.directoryContents.set(result);
        }
        this.selectedIds.set(new Set());
      },
      error: (err) => {
        this.toastService.emitErrorOrWarning('Failed to load directory: ' + err.message, 'error');
      }
    });
  }

  refreshDirectory() {
    const path = this.currentPath();
    // get current scroll position
    this.setRefreshState(this.getParentScrollContainer()?.scrollTop, {
      index: this.sortCriteria().index,
      order: !this.sortCriteria().order
    });
    this.loadDirectory(path.length > 0 ? path.join('/') : undefined, true);
  }

  refreshSelectedDirectory(item: FileBrowseNode) {
    this.gqlService.getDirectoryMetadataQuery(
      this.currentPath().join('/') + '/' + item.node.name
    ).subscribe({
      next: (result) => {
        if (result.data) {
          this.directoryContents.update(contents => {
            const updatedData = contents.data!.map(entry => {
              if (entry.node.id === item.node.id && entry.node.isDir && result.data) {
                return {
                  ...entry,
                  node: {
                    ...entry.node,
                    size: result.data.totalSize,
                    lastModifyTime: result.data.lastModifiedTime
                  }
                };
              }
              return entry;
            });
            return { ...contents, data: updatedData };
          });
        }
      },
      error: (err) => {
        this.toastService.emitErrorOrWarning('Failed to refresh directory metadata: ' + err.message, 'error');
      }
    });
  }

  setRefreshState(scrollTop: number = 0, sortCriteria: SortCriterion = { index: 0, order: false }) {
    this.stateService.setState<ManagementRefreshState>(
      environment.management_api + environment.refreshKey + environment.scrollKey,
      { scrollPosition: scrollTop, sortCriteria: sortCriteria} as ManagementRefreshState,
      false
    );
  }

  // ─── Directory Navigation ──────────────────────────────────────────

  onClickFileBrowseNode(node: FileBrowseNode) {
    if(!node.node.isDir) {
      this.toggleSelection(node.node.id);
      return;
    };
    this.setRefreshState();
    this.currentPath.update(path => [...path, node.node.name]);
    this.pathHistoryService.pushNewPath(this.currentPath());
  }

  navigateToPath(path: string[]) {
    this.setRefreshState();
    this.currentPath.set(path);
  }

  // ─── Selection ─────────────────────────────────────────────────────

  toggleSelection(id: string) {
    this.selectedIds.update(ids => {
      const newIds = new Set(ids);
      if (newIds.has(id)) {
        newIds.delete(id);
      } else {
        newIds.add(id);
      }
      return newIds;
    });
  }

  toggleSelectAll() {
    const contents = this.directoryContents().data;
    if (!contents) return;

    const selectableItems = contents.filter(item => !item.node.isDir);
    const allSelected = selectableItems.length > 0
      && selectableItems.every(item => this.selectedIds().has(item.node.id));

    if (allSelected) {
      this.selectedIds.set(new Set());
    } else {
      this.selectedIds.set(new Set(selectableItems.map(item => item.node.id)));
    }
  }

  // ─── Sorting ───────────────────────────────────────────────────────

  getSortOptionForColumn(columnIndex: number, asc: ItemsSortOption, desc: ItemsSortOption): ItemsSortOption {
    this.sortCriteria.update(criteria => {
      if (criteria.index === columnIndex) {
        // Toggle sort order
        criteria.order = !criteria.order;
      } else {
        criteria.index = columnIndex;
        criteria.order = true;
      }
      return criteria;
    });
    return this.sortCriteria().order ? asc : desc;
  }

  sortItemsBy(columnIndex: number, contents: FileBrowseNode[] | null) {
    if (!contents) return;
    let sortedContents = [...contents];

    const option = (() => {
      switch(columnIndex){
        case 0:
          return this.getSortOptionForColumn(0, ItemsSortOption.NAME_ASC, ItemsSortOption.NAME_DESC);
        case 1:
          return this.getSortOptionForColumn(1, ItemsSortOption.SIZE_ASC, ItemsSortOption.SIZE_DESC);
        case 2:
          return this.getSortOptionForColumn(2, ItemsSortOption.DATE_ASC, ItemsSortOption.DATE_DESC);
        default:
          return ItemsSortOption.NAME_ASC;
      }
    })();

    sortedContents.sort(comparatorBySortOption(option))
    this.directoryContents.set({ ...this.directoryContents(), data: sortedContents });
  }

  // ─── Dialog Operations result ─────────────────────────────────────────────

  operationResult(result: boolean) {
    if (!result) return;
    else {
      this.refreshDirectory();
      this.selectedIds.set(new Set());
    }
  }

  // ─── DOM Utilities ─────────────────────────────────────────────────

  private getParentScrollContainer(): HTMLElement | null {
    return document.getElementById(environment.containerIds.rootMainContainerId);
  }

  scrollTo(position: number) {
    const mainContainer = this.getParentScrollContainer();
    if (mainContainer) {
      mainContainer.scrollTo({ top: position, behavior: 'smooth' });
    }
  }

  updateTableWidth(width: number) {
    this.tableWidth.set(width);
  }
}
