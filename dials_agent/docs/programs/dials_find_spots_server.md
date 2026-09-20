# dials.find_spots_server/client

## Introduction
A client/server version of dials.find_spots with additional analysis including
estimation of resolution limits. Intended for quick feedback of image quality
during grid scans and data collections.
On the server machine:
```
dials.find_spots_server [nproc=8] [port=1234]

```

On the client machine:
```
dials.find_spots_client [host=hostname] [port=1234] [nproc=8] /path/to/image.cbf

```

The client will return a short xml string indicating the number of spots found
and several estimates of the resolution limit.
e.g.:
```
<response>
<image>/path/to/image_0001.cbf</image>
<spot_count>352</spot_count>
<spot_count_no_ice>263</spot_count_no_ice>
<d_min>1.46</d_min>
<d_min_method_1>1.92</d_min_method_1>
<d_min_method_2>1.68</d_min_method_2>
<total_intensity>56215</total_intensity>
</response>

```

`spot_count` is the total number of spots found in given image
`spot_count_no_ice` is the number of spots found excluding those at resolutions
where ice rings may be found
`d_min_method_1` is equivalent to distl’s resolution estimate method 1
`d_min_method_2` is equivalent to distl’s resolution estimate method 2
`total_intensity` is the total intensity of all strong spots excluding those
at resolutions where ice rings may be found

Any valid `dials.find_spots` parameter may be passed to
`dials.find_spots_client`, e.g.:
```
dials.find_spots_client /path/to/image.cbf min_spot_size=2 d_min=2

```

To stop the server:
```
dials.find_spots_client stop [host=hostname] [port=1234]

```

## Basic parameters
```
nproc = Auto
port = 1701

```

## Full parameter definitions
```
nproc = Auto
  .type = int(value_min=1, allow_none=True)
port = 1701
  .type = int(value_min=1, allow_none=True)

```