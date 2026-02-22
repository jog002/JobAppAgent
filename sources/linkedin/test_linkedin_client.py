#!/usr/bin/env python3
"""Test the updated linkedin_client module."""

import logging
import linkedin_client

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_search_jobs():
    """Test search_jobs function."""
    print("\n" + "="*80)
    print("TEST: search_jobs")
    print("="*80)

    try:
        jobs = linkedin_client.search_jobs(
            keywords="software engineer",
            location="Remote",
            limit=5
        )

        print(f"\n✅ search_jobs returned {len(jobs)} jobs")

        for i, job in enumerate(jobs[:3], 1):
            print(f"\nJob {i}:")
            print(f"  ID: {job.get('id')}")
            print(f"  URL: {job.get('url')}")

        return True

    except Exception as e:
        print(f"\n❌ search_jobs failed: {e}")
        return False


def test_get_job_details():
    """Test get_job_details function."""
    print("\n" + "="*80)
    print("TEST: get_job_details")
    print("="*80)

    # First get some jobs to get a real job ID
    try:
        jobs = linkedin_client.search_jobs("python developer", limit=1)
        if not jobs:
            print("⚠️  No jobs found to test with")
            return False

        job_id = jobs[0].get('id')
        print(f"\nTesting with job ID: {job_id}")

        details = linkedin_client.get_job_details(job_id)

        if details:
            print(f"\n✅ get_job_details succeeded")
            print(f"\nJob Details Keys: {list(details.keys())[:10]}")

            # Print some key fields if available
            for key in ['title', 'company', 'location', 'description']:
                if key in details:
                    value = str(details[key])[:100]
                    print(f"  {key}: {value}...")

            return True
        else:
            print("\n❌ get_job_details returned None")
            return False

    except Exception as e:
        print(f"\n❌ get_job_details failed: {e}")
        return False


def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("LINKEDIN CLIENT TESTS")
    print("="*80)

    results = {}

    results['search_jobs'] = test_search_jobs()
    results['get_job_details'] = test_get_job_details()

    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")

    all_passed = all(results.values())
    print("\n" + "="*80)
    if all_passed:
        print("ALL TESTS PASSED")
    else:
        print("SOME TESTS FAILED")
    print("="*80)

    return 0 if all_passed else 1


if __name__ == "__main__":
    exit(main())
