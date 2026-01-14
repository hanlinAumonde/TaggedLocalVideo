export interface ResultState<T> {
    loading: boolean;
    error: string | null
    data: T | null;
}