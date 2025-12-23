# Performance Best Practices

## Overview

Performance optimization is critical for building scalable, responsive applications. This guide establishes best practices for maximizing CPU and memory utilization across all languages and frameworks supported by the project template.

The fundamental principle is to **always implement async/concurrent patterns** to maximize hardware utilization and ensure applications can handle concurrent workloads efficiently.

## Python Performance Optimization

### Async and Concurrent Patterns

Always implement asynchronous and concurrent patterns in Python to maximize CPU and memory utilization:

- **asyncio**: Use for I/O-bound operations and network communication
- **threading**: Use for I/O-bound tasks where asyncio is not suitable
- **multiprocessing**: Use for CPU-bound operations that require true parallelism

Example asyncio pattern:

```python
import asyncio

async def fetch_data(url):
    """Fetch data asynchronously"""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()

async def process_multiple_urls(urls):
    """Process multiple URLs concurrently"""
    tasks = [fetch_data(url) for url in urls]
    results = await asyncio.gather(*tasks)
    return results

# Run async code
asyncio.run(process_multiple_urls(['http://...', 'http://...']))
```

### Modern Python Optimizations (Python 3.12+)

Python 3.12 and 3.13 introduce several features and optimizations that should be leveraged for better performance:

#### Dataclasses

Use `@dataclass` for structured data to reduce memory overhead and improve performance compared to regular classes:

```python
from dataclasses import dataclass, field
from typing import List

@dataclass
class User:
    """User data structure with automatic __init__, __repr__, and __eq__"""
    id: int
    name: str
    email: str
    active: bool = True
    tags: List[str] = field(default_factory=list)

@dataclass(frozen=True, slots=True)
class ImmutableUser:
    """Frozen dataclass with slots for even better memory efficiency"""
    id: int
    name: str
    email: str
```

Benefits of dataclasses:
- Automatic generation of `__init__`, `__repr__`, `__eq__`, and other special methods
- Reduced memory overhead compared to regular classes
- Better IDE support and type checking
- Cleaner, more readable code

#### Type Hints

Use comprehensive typing annotations for better optimization and IDE support. Type hints enable:
- Better static analysis and early error detection
- Improved IDE autocomplete and refactoring
- Better performance in PyCharm and similar IDEs
- Clearer code intent and documentation

```python
from typing import List, Dict, Optional, Union, Callable
from dataclasses import dataclass

@dataclass
class DataProcessor:
    """Type-hinted data processor"""

    def process_items(self, items: List[str]) -> Dict[str, int]:
        """Process items and return counts"""
        return {item: len(item) for item in items}

    def apply_transformation(
        self,
        data: List[Dict[str, any]],
        transformer: Callable[[Dict[str, any]], Dict[str, any]]
    ) -> List[Dict[str, any]]:
        """Apply transformation function to data"""
        return [transformer(item) for item in data]

    def safe_get_value(self, data: Dict[str, any], key: str) -> Optional[str]:
        """Safely retrieve value from dictionary"""
        return data.get(key)
```

#### Advanced Memory-Efficient Patterns

Utilize slots and frozen dataclasses for memory-constrained applications:

```python
from dataclasses import dataclass

# Use slots to eliminate __dict__ overhead
@dataclass(slots=True)
class Point:
    """Memory-efficient point class"""
    x: float
    y: float
    z: float

# Frozen dataclasses for immutable data structures
@dataclass(frozen=True, slots=True)
class Coordinate:
    """Immutable coordinate with minimal memory overhead"""
    latitude: float
    longitude: float
    altitude: float

    def __hash__(self):
        """Enable use as dictionary key"""
        return hash((self.latitude, self.longitude, self.altitude))

# Example: Memory comparison
# Regular class with __dict__: ~360 bytes per instance
# Dataclass with slots: ~56 bytes per instance
# 6x memory savings for large collections
```

## Go Performance Optimization

Go's runtime and language design provide excellent performance characteristics. Leverage these features:

### Goroutines and Concurrency

Use goroutines and channels for concurrent operations:

```go
package main

import (
    "fmt"
    "sync"
)

func fetchData(id int, results chan<- string, wg *sync.WaitGroup) {
    defer wg.Done()
    // Simulate work
    results <- fmt.Sprintf("Data for ID %d", id)
}

func processMultiple(ids []int) []string {
    results := make(chan string, len(ids))
    var wg sync.WaitGroup

    // Launch goroutine for each ID
    for _, id := range ids {
        wg.Add(1)
        go fetchData(id, results, &wg)
    }

    // Wait for completion and collect results
    go func() {
        wg.Wait()
        close(results)
    }()

    var output []string
    for result := range results {
        output = append(output, result)
    }
    return output
}
```

### Connection Pooling and Resource Management

Implement proper connection pooling and resource management:

```go
import (
    "database/sql"
    "database/sql/driver"
)

func setupDatabase() *sql.DB {
    db, _ := sql.Open("postgres", "connection-string")

    // Configure connection pool
    db.SetMaxOpenConns(25)      // Maximum concurrent connections
    db.SetMaxIdleConns(5)       // Keep 5 idle connections
    db.SetConnMaxLifetime(time.Hour) // Recycle connections hourly

    return db
}
```

## Networking Application Optimizations

For high-performance networking applications, implement these advanced optimizations:

### eBPF/XDP for Kernel-Level Processing

eBPF (extended Berkeley Packet Filter) and XDP (eXpress Data Path) enable packet processing at the kernel level with minimal overhead:

```go
// Conceptual example of XDP usage
// XDP programs run in the kernel before packets reach user space
// Provides ~10x performance improvement for packet filtering

import "github.com/cilium/ebpf"

func loadXDPProgram() (*ebpf.Program, error) {
    spec, _ := ebpf.LoadCollectionSpec("xdp_program.o")
    return spec.LoadAndAssign(nil)
}
```

Key benefits:
- Process packets at kernel level (before network stack)
- Drop malicious packets before user-space overhead
- Can achieve line-rate performance for 10Gbps+ networks
- Ideal for DDoS mitigation and packet filtering

### AF_XDP for High-Performance User-Space Processing

AF_XDP (AF_XDP socket) enables high-performance packet processing in user space while bypassing kernel overhead:

```go
// AF_XDP allows direct access to packet buffers
// ~3-5x faster than traditional socket operations
// Typical use: network appliances, packet capture, filtering

type AFXDPSocket struct {
    umem *ebpf.Map
    fq   *ebpf.Map  // Fill queue
    cq   *ebpf.Map  // Completion queue
}

func (s *AFXDPSocket) ProcessPackets() error {
    // Direct memory access to packet buffers without copying
    // Batch processing for better throughput
    return nil
}
```

### NUMA-Aware Memory Allocation

For systems with Non-Uniform Memory Access (NUMA), optimize memory allocation:

```go
// NUMA-aware allocation example
import "golang.org/x/sys/unix"

func allocateNumaMemory(size int, numaNode int) ([]byte, error) {
    // Allocate memory on specific NUMA node
    // Reduces cross-node memory latency
    // Critical for systems with >1 NUMA node

    // Use numactl or OS-specific APIs
    // Go example using syscall
    return unix.Mmap(-1, 0, size,
        unix.PROT_READ|unix.PROT_WRITE,
        unix.MAP_PRIVATE|unix.MAP_ANONYMOUS)
}
```

### CPU Affinity and Core Pinning

Pin goroutines or threads to specific CPU cores for cache efficiency:

```go
import "runtime"

func setupCPUAffinity(coreID int) {
    runtime.LockOSThread()
    // Pin current thread to CPU core
    // Benefits: improved cache locality, fewer context switches
}

func processByCore(coreID int, data []int) {
    setupCPUAffinity(coreID)
    // Process data on dedicated core
    for _, item := range data {
        // Work happens on single core
        _ = item * 2
    }
}
```

### Zero-Copy Networking Techniques

Implement zero-copy patterns to avoid data duplication:

```go
import (
    "io"
    "net"
)

// Zero-copy file transmission
func sendFileZeroCopy(conn net.Conn, file io.Reader) error {
    // Use sendfile syscall (zero-copy kernel operation)
    if f, ok := file.(*os.File); ok {
        // sendfile copies data from kernel buffer directly to socket
        // No user-space buffer copy required
        _, err := io.Copy(conn, f)
        return err
    }
    return nil
}

// Memory pool for buffer reuse
type BufferPool struct {
    pool chan []byte
}

func (bp *BufferPool) Get(size int) []byte {
    select {
    case b := <-bp.pool:
        return b[:size]
    default:
        return make([]byte, size)
    }
}

func (bp *BufferPool) Put(b []byte) {
    select {
    case bp.pool <- b:
    default:
        // Pool full, discard
    }
}
```

### Connection Pooling and Load Balancing

Implement efficient connection management:

```go
import (
    "net/http"
    "sync"
)

type ConnectionPool struct {
    connections []*http.Client
    index       int
    mu          sync.Mutex
}

func (cp *ConnectionPool) NextConnection() *http.Client {
    cp.mu.Lock()
    defer cp.mu.Unlock()

    client := cp.connections[cp.index]
    cp.index = (cp.index + 1) % len(cp.connections)
    return client
}

// Configure HTTP client for optimal performance
func createOptimalHTTPClient() *http.Client {
    return &http.Client{
        Transport: &http.Transport{
            MaxIdleConns:          100,
            MaxIdleConnsPerHost:   10,
            MaxConnsPerHost:       100,
            IdleConnTimeout:       90 * time.Second,
            DisableKeepAlives:     false,
            DisableCompression:    false,
            ExpectContinueTimeout: 1 * time.Second,
        },
        Timeout: 30 * time.Second,
    }
}
```

## Memory Management

Optimize memory usage and garbage collection:

### Memory Allocation Strategies

1. **Reuse buffers** - Allocate once, reuse multiple times
2. **Batch processing** - Process multiple items in a single allocation
3. **Lazy initialization** - Only allocate when needed
4. **Pool patterns** - Maintain pools of reusable objects

```python
# Python example with object pooling
from queue import Queue
from dataclasses import dataclass

@dataclass
class DataBuffer:
    """Reusable data buffer"""
    data: bytearray
    size: int = 0

    def reset(self):
        """Reset buffer for reuse"""
        self.size = 0
        self.data = bytearray(len(self.data))

class BufferPool:
    """Pool of reusable buffers"""
    def __init__(self, size: int, buffer_capacity: int = 4096):
        self.queue: Queue = Queue(maxsize=size)
        for _ in range(size):
            self.queue.put(DataBuffer(bytearray(buffer_capacity)))

    def acquire(self) -> DataBuffer:
        return self.queue.get()

    def release(self, buffer: DataBuffer):
        buffer.reset()
        self.queue.put(buffer)
```

### Cache Locality

Optimize data structures for CPU cache efficiency:

```go
// Good: Arrays/slices provide cache locality
type Pipeline struct {
    stages []Stage  // Contiguous memory, cache-friendly
}

// Less optimal: Linked structures with pointers
type Node struct {
    value int
    next  *Node  // Pointer chasing, cache misses
}
```

## I/O Operations

### Non-Blocking I/O

Use non-blocking I/O patterns to prevent thread/goroutine blocking:

```python
import asyncio

async def handle_io_non_blocking():
    """Non-blocking I/O using asyncio"""
    reader, writer = await asyncio.open_connection('localhost', 8080)

    # Write without blocking
    writer.write(b'request data')
    await writer.drain()

    # Read without blocking
    data = await reader.read(4096)
    return data
```

### Buffering and Batching

Implement buffering and batching for better throughput:

```go
// Batch processing pattern
func processBatched(items <-chan int, batchSize int) {
    batch := make([]int, 0, batchSize)

    for item := range items {
        batch = append(batch, item)

        if len(batch) >= batchSize {
            processBatch(batch)
            batch = batch[:0] // Reset without deallocating
        }
    }

    // Process remaining items
    if len(batch) > 0 {
        processBatch(batch)
    }
}

func processBatch(items []int) {
    // Process items in batch for better performance
    // Single system call handles multiple items
}
```

## Database Access

### Connection Pooling

Always implement connection pooling to reuse database connections:

```python
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

# Python with SQLAlchemy
engine = create_engine(
    'postgresql://user:password@host/db',
    poolclass=QueuePool,
    pool_size=10,              # Connections to keep in pool
    max_overflow=20,           # Additional connections when needed
    pool_recycle=3600,         # Recycle connections hourly
    pool_pre_ping=True         # Test connection before using
)
```

### Prepared Statements

Use prepared statements to improve query performance and security:

```python
from sqlalchemy import text

# Prepared statement pattern
query = text("""
    SELECT * FROM users
    WHERE id = :user_id AND active = :active
""")

result = engine.execute(query, user_id=123, active=True)
```

### Query Optimization

Optimize database queries for better performance:

```python
# Bad: N+1 query problem
users = db.session.query(User).all()
for user in users:
    print(user.posts)  # Additional query for each user

# Good: Use eager loading
from sqlalchemy.orm import joinedload

users = db.session.query(User).options(
    joinedload(User.posts)
).all()

# Good: Use batch loading
from sqlalchemy.orm import selectinload

users = db.session.query(User).options(
    selectinload(User.posts)
).all()
```

### Index Strategy

Create indexes on frequently queried columns:

```sql
-- Index for common queries
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_posts_user_id ON posts(user_id);
CREATE INDEX idx_posts_created_at ON posts(created_at DESC);

-- Composite index for multi-column queries
CREATE INDEX idx_users_active_created ON users(active, created_at DESC);
```

## Summary

Performance optimization requires a multi-faceted approach:

1. **Always use async/concurrent patterns** for I/O-bound operations
2. **Leverage modern language features** (dataclasses, type hints, slots in Python)
3. **Implement proper resource pooling** (connections, buffers, threads)
4. **Optimize for cache locality** and memory access patterns
5. **Use advanced networking techniques** for high-performance applications
6. **Batch operations** where possible to reduce overhead
7. **Monitor and measure** performance to identify bottlenecks

Apply these best practices consistently across your codebase to build responsive, scalable applications.
