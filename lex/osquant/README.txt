## this is the image that gave me a working Web Client Gateway!!!
https://osquant.com/papers/dockerising-interactive-brokers-client-portal-api/  <--- It worked!!!!
      -  the github:  https://github.com/robolyst/ibportal

dradrian/ibportal

## 2023-09-03:
   - process to bring up the Web Client Gateway and connect
   1. docker run --name ibportal --network my_network -p 5000:5000 dradrian/ibportal
   2. go to firefox browser (works best for logins) and login at https://localhost:5000
   3. docker run -it --name ib_test --network my_network test_ib_portal bash
   4. run python ib_cleint_test.py 
        - this create another client container that queries the WEB Api via the Web Client Gateway.

  --- Web Client API: https://interactivebrokers.github.io/cpwebapi/endpoints


