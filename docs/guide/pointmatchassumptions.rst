Pointmatch Assumptions
======================
Generally, I would reccomend adopting a set of conventions that constrain the
relationship between data in the 'tile' and 'pointmatch' databases.  These conventions are informed
in large part based upon how the EMAligner https://github.com/khaledkhairy/EM_aligner
assumes they are related, when using them to solve alignment problems. 


tile_owners = pointmatch_owners
-------------------------------
Particularly on deployments which have only a single render service, this will save you
from having to redefine the default owner in the :class:`renderapi.render.Render` or override 
it at each step. Make all stacks related to a dataset owned by a single owner, and make all 
pointmatch collections owned by that same owner. 

.. _group-section-explanation:

groupId=sectionId and id=tileId
----------------------------
Or more verbosely, groupId/qGroupId/pGroupId = sectionId and pId/qId/id = tileId.
Groups thus correspond to what section the point match is from and the id's correspond to what tile
they are from. 
Technically, there is no need to make this association, and none of the render web services strictly require it.
However, if you want to use the pointmatch results in combination with the tile services,
it will be far easier if there is a strict mapping between these two databases.
In addition, tools like EMAligner and ndviz are presently written in a way that assumes this mapping is held,
so you need to make the same assumption if you want to use those services. 

Know your 'local'
-------------------------------------------------------------------
Write all pointmatches between tiles in a consistent 'local' coordinate system
and make that local coordinate system the raw image space given by rendering the tile
using :func:`renderapi.image.get_tile_image_data` with normalizeForMatching=True and scale=1.0. 

This would be conceptually simple, if the 'local' meant the same as 
:class:`renderapi.coordinate` module defines local to mean, 
namely the raw image space, with the upper left hand pixel at 0,0 and positive x to the right
and positive y down.

However, in some deployments of render this is not the case, and you might find that 
rendering a tile using normalizeForMatching=True does not produce a raw image tile. 
In fact it might render blank data in some circumstances if you have more than 1 transformation. 

This is because, at Janelia the EMAligner was developed on TEM images that need a lens correction
transformation, and the pointmatches are defined on the 'local' coordinate system after lens correction.  
This simplifies solving for the non-lens component of the transformation, as the EMAligner only
needs to specify the single transformation that brings 'local' pointmatches into 'global' alignment
and can safely disregard the non-linear effects of the lens correction. 

However, it produces the confusing result that mapping the 'local' point matches coordinates
through :func:`renderapi.coordinate.local_to_world_coordinates` does not give the correct result,
and you have to have a second stack with lens correction transformations removed in order to map
point match coordinates from local to world coordinates accurately using the coordinate mapping service. 

More discussion on this at https://github.com/saalfeldlab/render/issues/13, 
https://github.com/saalfeldlab/render/issues/31.

I implemented an alternative strategy at 
https://github.com/saalfeldlab/render/pull/29
which adds a removeAllOption=True to many render calls 
which simply removes all transformations from the tilespec before returning or rendering.
In applications where non-linear lens corrections are minimal, this simplifies things. 

However for TEM or other applications with stereotyped non-linear transformations, 
it will make using the EMAligner to solve alignment problems more difficult, 
as the EMAligner doesn't know that it should map the pointmatches into the post non-linear correction
space before attemptign to solve and isn't presently written to do this.



