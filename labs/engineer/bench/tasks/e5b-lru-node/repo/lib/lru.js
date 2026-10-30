export class LRU {
  constructor(capacity) {
    this.capacity = capacity;
    this.map = new Map();
    this.size = 0;
  }

  get(key) {
    if (!this.map.has(key)) return undefined;
    return this.map.get(key);
  }

  set(key, value) {
    this.map.set(key, value);
    this.size += 1;
    while (this.size > this.capacity) {
      const oldest = this.map.keys().next().value;
      this.map.delete(oldest);
      this.size -= 1;
    }
  }
}
