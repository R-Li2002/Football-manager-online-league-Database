from database import run_manual_runtime_fallback


def main() -> None:
    run_manual_runtime_fallback()
    print("Manual runtime schema repair completed. Check output/logs/schema_bootstrap.log for details.")


if __name__ == "__main__":
    main()
