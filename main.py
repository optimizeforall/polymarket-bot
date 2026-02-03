import time
import signal
import sys
sys.path.insert(0, 'src/core')
sys.path.insert(0, 'src/trading')

from fetcher import get_btc_price
from logger import ensure_headers, fetch_with_retry, log_price, get_stats, Colors

INTERVAL = 5
running = True

def handle_signal(signum, frame):
    global running
    print(f"\n{Colors.CYAN}{'='*60}{Colors.RESET}")
    print(f"{Colors.YELLOW}Shutting down gracefully...{Colors.RESET}")
    
    stats = get_stats()
    if stats:
        print(f"{Colors.CYAN}Session Stats:{Colors.RESET}")
        print(f"  {Colors.WHITE}•{Colors.RESET} Prices logged: {Colors.BOLD}{stats['count']}{Colors.RESET}")
        print(f"  {Colors.WHITE}•{Colors.RESET} Price range: {Colors.GREEN}${stats['min']:,.2f}{Colors.RESET} - {Colors.RED}${stats['max']:,.2f}{Colors.RESET}")
        print(f"  {Colors.WHITE}•{Colors.RESET} Range span: {Colors.CYAN}${stats['range']:,.2f}{Colors.RESET}")
    
    print(f"{Colors.CYAN}{'='*60}{Colors.RESET}")
    running = False

signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGTERM, handle_signal)

def main():
    ensure_headers()
    print(f"\n{Colors.CYAN}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.WHITE}🚀 BTC Price Logger{Colors.RESET} {Colors.YELLOW}(Production){Colors.RESET}")
    print(f"{Colors.CYAN}{'='*60}{Colors.RESET}")
    print(f"{Colors.WHITE}•{Colors.RESET} Logging interval: {Colors.BOLD}{INTERVAL}{Colors.RESET} seconds")
    print(f"{Colors.WHITE}•{Colors.RESET} Press {Colors.YELLOW}Ctrl+C{Colors.RESET} to stop")
    print(f"{Colors.CYAN}{'='*60}{Colors.RESET}\n")
    
    while running:
        iteration_start = time.time()
        
        # Fetch with retry logic
        data = fetch_with_retry(get_btc_price)
        log_price(data)
        
        # Precise timing - ensure exactly INTERVAL seconds between iterations
        # This minimizes jitter in timestamp spacing
        elapsed = time.time() - iteration_start
        sleep_time = max(0, INTERVAL - elapsed)
        if sleep_time > 0:
            time.sleep(sleep_time)

if __name__ == "__main__":
    main()